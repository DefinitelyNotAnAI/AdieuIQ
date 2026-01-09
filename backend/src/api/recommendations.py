"""
Recommendation API endpoints.

Implements recommendation generation, outcome updates, and acceptance tracking
per contracts/openapi.yaml.

Constitutional Compliance (NON-NEGOTIABLE):
- Azure AD authentication required for all endpoints
- RBAC enforcement (api://adieuiq/Recommendations.Generate scope)
- OpenTelemetry instrumentation for all requests
- Content Safety validation via orchestrator (Constitutional Principle III)
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..core.auth import get_current_user, require_scope
from ..core.observability import get_tracer
from ..models.recommendation import OutcomeStatus
from ..services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


# Request/Response Models
class RecommendationResponse(BaseModel):
    """Single recommendation response."""

    recommendation_id: str
    recommendation_type: str  # Adoption or Upsell
    text_description: str = Field(..., max_length=1000)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    data_sources: list[dict[str, Any]]
    reasoning_chain: dict[str, Any]


class GenerateRecommendationsResponse(BaseModel):
    """Response for recommendation generation."""

    customer_id: str
    adoption_recommendations: list[RecommendationResponse]
    upsell_recommendations: list[RecommendationResponse]
    generation_time_ms: int = Field(..., description="Total generation time in milliseconds")
    cached: bool = Field(..., description="Whether results came from cache")
    orchestration_metadata: dict[str, Any]


class UpdateOutcomeRequest(BaseModel):
    """Request to update recommendation outcome."""

    outcome_status: str = Field(
        ..., description="New status: Delivered, Accepted, or Declined"
    )
    agent_id: str = Field(..., description="Support agent performing the update")
    feedback: str | None = Field(None, max_length=500, description="Optional feedback text")


class AcceptanceRequest(BaseModel):
    """Request to track recommendation acceptance (T038a)."""

    agent_confirmed: bool = Field(
        ..., description="Whether agent confirmed delivery to customer"
    )
    feedback: str | None = Field(
        None, max_length=500, description="Optional feedback from agent or customer"
    )


class AcceptanceResponse(BaseModel):
    """Response for acceptance tracking."""

    recommendation_id: str
    outcome_status: str
    acceptance_timestamp: str
    agent_id: str
    success: bool


@router.post(
    "/{customer_id}",
    response_model=GenerateRecommendationsResponse,
    summary="Generate recommendations for customer",
    description="Trigger multi-agent orchestration to generate adoption + upsell recommendations. Requires Recommendations.Generate scope.",
    status_code=status.HTTP_200_OK,
)
async def generate_recommendations(
    customer_id: UUID,
    force_refresh: bool = Query(
        False, description="Force fresh generation, bypass 24-hour cache"
    ),
    current_user: dict = Depends(get_current_user),
    _scope_check: None = Depends(require_scope("api://adieuiq/Recommendations.Generate")),
) -> GenerateRecommendationsResponse:
    """
    Generate recommendations for a customer (T037).

    Orchestrates multi-agent workflow:
    1. Retrieval Agent (queries Fabric IQ + Foundry IQ in parallel)
    2. Sentiment Agent (analyzes interaction history in parallel with Retrieval)
    3. Reasoning Agent (generates candidate recommendations)
    4. Validation Agent (Content Safety + duplicate check + confidence filter)

    Results are cached in Cosmos DB with 12-month TTL. Returns cached results
    if generated within last 24 hours (unless force_refresh=True).

    Args:
        customer_id: Target customer UUID
        force_refresh: Bypass cache and regenerate (default False)
        current_user: Authenticated user from Azure AD token
        _scope_check: RBAC scope validation

    Returns:
        GenerateRecommendationsResponse with adoption + upsell recommendations

    Raises:
        HTTPException: 401 if unauthorized, 500 if generation fails
    """
    with tracer.start_as_current_span("api.recommendations.generate") as span:
        span.set_attribute("customer_id", str(customer_id))
        span.set_attribute("force_refresh", force_refresh)
        span.set_attribute("user_id", current_user.get("sub"))

        try:
            recommendation_service = RecommendationService()
            result = await recommendation_service.generate_recommendations(
                customer_id=customer_id, force_refresh=force_refresh
            )

            logger.info(
                f"Generated recommendations for customer {customer_id}: "
                f"adoption={len(result['adoption_recommendations'])}, "
                f"upsell={len(result['upsell_recommendations'])}, "
                f"cached={result.get('cached', False)} "
                f"(user: {current_user.get('sub')})"
            )

            span.set_attribute("adoption_count", len(result["adoption_recommendations"]))
            span.set_attribute("upsell_count", len(result["upsell_recommendations"]))
            span.set_attribute("cached", result.get("cached", False))
            span.set_attribute("generation_time_ms", result.get("generation_time_ms", 0))

            # Convert to response model
            return GenerateRecommendationsResponse(
                customer_id=str(customer_id),
                adoption_recommendations=[
                    RecommendationResponse(**rec)
                    for rec in result["adoption_recommendations"]
                ],
                upsell_recommendations=[
                    RecommendationResponse(**rec)
                    for rec in result["upsell_recommendations"]
                ],
                generation_time_ms=result.get("generation_time_ms", 0),
                cached=result.get("cached", False),
                orchestration_metadata=result.get("orchestration_metadata", {}),
            )

        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}", exc_info=True)
            span.set_attribute("error", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Recommendation generation failed: {str(e)}",
            )


@router.put(
    "/{recommendation_id}/outcome",
    response_model=dict[str, Any],
    summary="Update recommendation outcome",
    description="Update recommendation status to Delivered/Accepted/Declined. Implements audit trail per FR-020.",
)
async def update_recommendation_outcome(
    recommendation_id: UUID,
    request: UpdateOutcomeRequest,
    current_user: dict = Depends(get_current_user),
    _scope_check: None = Depends(require_scope("api://adieuiq/Recommendations.Generate")),
) -> dict[str, Any]:
    """
    Update recommendation outcome (T038).

    Updates outcome_status and tracks audit trail:
    - delivered_by_agent_id: User who performed the update
    - outcome_timestamp: When update occurred
    - feedback: Optional feedback text

    Args:
        recommendation_id: Target recommendation UUID
        request: Update request with outcome_status, agent_id, feedback
        current_user: Authenticated user from Azure AD token
        _scope_check: RBAC scope validation

    Returns:
        Success response with updated recommendation_id

    Raises:
        HTTPException: 400 if invalid status, 404 if not found, 500 if update fails
    """
    with tracer.start_as_current_span("api.recommendations.update_outcome") as span:
        span.set_attribute("recommendation_id", str(recommendation_id))
        span.set_attribute("outcome_status", request.outcome_status)
        span.set_attribute("user_id", current_user.get("sub"))

        try:
            # Validate outcome_status
            try:
                outcome_status = OutcomeStatus(request.outcome_status)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid outcome_status: {request.outcome_status}. Must be Pending, Delivered, Accepted, or Declined.",
                )

            recommendation_service = RecommendationService()
            success = await recommendation_service.update_recommendation_outcome(
                recommendation_id=recommendation_id,
                outcome_status=outcome_status,
                agent_id=request.agent_id,
                feedback=request.feedback,
            )

            if not success:
                logger.warning(f"Recommendation {recommendation_id} not found")
                span.set_attribute("found", False)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Recommendation {recommendation_id} not found",
                )

            logger.info(
                f"Updated recommendation {recommendation_id} to {request.outcome_status} "
                f"(agent: {request.agent_id}, user: {current_user.get('sub')})"
            )
            span.set_attribute("success", True)

            return {
                "recommendation_id": str(recommendation_id),
                "outcome_status": request.outcome_status,
                "agent_id": request.agent_id,
                "outcome_timestamp": datetime.utcnow().isoformat(),
                "success": True,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update recommendation outcome: {e}", exc_info=True)
            span.set_attribute("error", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update recommendation outcome: {str(e)}",
            )


@router.post(
    "/{recommendation_id}/acceptance",
    response_model=AcceptanceResponse,
    summary="Track recommendation acceptance",
    description="Mark recommendation as delivered and track acceptance per FR-020 and SC-002.",
    status_code=status.HTTP_200_OK,
)
async def track_recommendation_acceptance(
    recommendation_id: UUID,
    request: AcceptanceRequest,
    current_user: dict = Depends(get_current_user),
    _scope_check: None = Depends(require_scope("api://adieuiq/Recommendations.Generate")),
) -> AcceptanceResponse:
    """
    Track recommendation acceptance (T038a).

    This endpoint implements:
    - FR-020: Audit trail for recommendation delivery
    - SC-002: Track acceptance rate for accuracy measurement

    When agent_confirmed=True, updates outcome_status to Delivered (or Accepted if customer confirmed).
    Stores acceptance timestamp and optional feedback for analytics.

    Args:
        recommendation_id: Target recommendation UUID
        request: Acceptance request with agent_confirmed and optional feedback
        current_user: Authenticated user from Azure AD token
        _scope_check: RBAC scope validation

    Returns:
        AcceptanceResponse with updated status and timestamp

    Raises:
        HTTPException: 404 if not found, 500 if update fails
    """
    with tracer.start_as_current_span("api.recommendations.track_acceptance") as span:
        span.set_attribute("recommendation_id", str(recommendation_id))
        span.set_attribute("agent_confirmed", request.agent_confirmed)
        span.set_attribute("user_id", current_user.get("sub"))

        try:
            agent_id = current_user.get("sub", "unknown")

            # Determine outcome status based on confirmation
            # If agent confirmed delivery, mark as Delivered (customer may accept/decline later)
            outcome_status = (
                OutcomeStatus.DELIVERED if request.agent_confirmed else OutcomeStatus.PENDING
            )

            recommendation_service = RecommendationService()
            success = await recommendation_service.update_recommendation_outcome(
                recommendation_id=recommendation_id,
                outcome_status=outcome_status,
                agent_id=agent_id,
                feedback=request.feedback,
            )

            if not success:
                logger.warning(f"Recommendation {recommendation_id} not found")
                span.set_attribute("found", False)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Recommendation {recommendation_id} not found",
                )

            acceptance_timestamp = datetime.utcnow().isoformat()

            logger.info(
                f"Tracked acceptance for recommendation {recommendation_id}: "
                f"agent_confirmed={request.agent_confirmed}, status={outcome_status.value} "
                f"(agent: {agent_id})"
            )
            span.set_attribute("success", True)
            span.set_attribute("outcome_status", outcome_status.value)

            return AcceptanceResponse(
                recommendation_id=str(recommendation_id),
                outcome_status=outcome_status.value,
                acceptance_timestamp=acceptance_timestamp,
                agent_id=agent_id,
                success=True,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to track recommendation acceptance: {e}", exc_info=True)
            span.set_attribute("error", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to track recommendation acceptance: {str(e)}",
            )


@router.get(
    "/{recommendation_id}/explainability",
    response_model=dict[str, Any],
    summary="Get recommendation explainability",
    description="Retrieve agent contributions for transparency (User Story 4). Requires Recommendations.Generate scope.",
)
async def get_recommendation_explainability(
    recommendation_id: UUID,
    current_user: dict = Depends(get_current_user),
    _scope_check: None = Depends(require_scope("api://adieuiq/Recommendations.Generate")),
) -> dict[str, Any]:
    """
    Get recommendation explainability (User Story 4 - T060).

    Returns recommendation with full agent contribution breakdown:
    - Retrieval Agent: Usage data + knowledge articles retrieved
    - Sentiment Agent: Sentiment score + factors identified
    - Reasoning Agent: Candidate generation logic
    - Validation Agent: Content Safety + duplicate + confidence filtering

    Args:
        recommendation_id: Target recommendation UUID
        current_user: Authenticated user from Azure AD token
        _scope_check: RBAC scope validation

    Returns:
        Dictionary with recommendation and agent_contributions array

    Raises:
        HTTPException: 404 if not found, 500 if retrieval fails
    """
    with tracer.start_as_current_span("api.recommendations.explainability") as span:
        span.set_attribute("recommendation_id", str(recommendation_id))
        span.set_attribute("user_id", current_user.get("sub"))

        try:
            logger.info(
                f"Fetching explainability for recommendation {recommendation_id}",
                extra={"user_id": current_user.get("sub")}
            )

            # Initialize recommendation service
            recommendation_service = RecommendationService()

            # Retrieve recommendation with agent contributions (T060)
            result = await recommendation_service.get_recommendation_explainability(
                recommendation_id
            )

            if not result:
                logger.warning(f"Recommendation {recommendation_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Recommendation {recommendation_id} not found"
                )

            logger.info(
                f"Successfully retrieved explainability for {recommendation_id}: "
                f"{len(result.get('agent_contributions', []))} contributions"
            )
            span.set_attribute("contribution_count", len(result.get("agent_contributions", [])))

            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Failed to retrieve explainability for {recommendation_id}: {e}",
                exc_info=True
            )
            span.set_attribute("error", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve explainability: {str(e)}"
            ) from e

