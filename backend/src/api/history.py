"""
History API endpoints.

Implements historical interaction and recommendation retrieval endpoints per contracts/openapi.yaml.

Constitutional Compliance (NON-NEGOTIABLE):
- Azure AD authentication required for all endpoints
- RBAC enforcement (api://adieuiq/History.Read scope)
- OpenTelemetry instrumentation for all requests
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..core.auth import get_current_user, require_scope
from ..core.observability import get_tracer
from ..services.customer_service import CustomerService
from ..services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

router = APIRouter(prefix="/customers", tags=["History"])


# Response Models (per OpenAPI spec)
class InteractionEvent(BaseModel):
    """Historical interaction event."""

    event_id: str
    customer_id: str
    event_type: str
    timestamp: str
    description: str
    sentiment_score: float = Field(..., ge=0.0, le=1.0)
    resolution_status: str
    tags: list[str] = Field(default_factory=list)


class PastRecommendation(BaseModel):
    """Historical recommendation with outcome."""

    recommendation_id: str
    customer_id: str
    recommendation_type: str
    recommendation_text: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reasoning_chain: dict[str, Any]
    generation_timestamp: str
    outcome_status: str
    delivered_by_agent_id: str | None = None
    outcome_timestamp: str | None = None


class CustomerHistoryResponse(BaseModel):
    """Combined historical timeline."""

    interactions: list[InteractionEvent]
    past_recommendations: list[PastRecommendation]


# Dependency injection
def get_customer_service() -> CustomerService:
    """Create CustomerService instance."""
    return CustomerService()


def get_recommendation_service() -> RecommendationService:
    """Create RecommendationService instance."""
    return RecommendationService()


@router.get(
    "/{customer_id}/history",
    response_model=CustomerHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get historical interactions and past recommendations",
    description="Returns 12-month timeline (FR-013)",
)
async def get_customer_history(
    customer_id: UUID,
    months: int = Query(default=12, ge=1, le=12, description="Number of months of history (1-12)"),
    current_user: dict[str, Any] = Depends(get_current_user),
    _: None = Depends(require_scope("api://adieuiq/History.Read")),
    customer_service: CustomerService = Depends(get_customer_service),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
) -> CustomerHistoryResponse:
    """
    Retrieve historical interactions and past recommendations for a customer.

    Per FR-013, supports retrieving up to 12 months of historical context including:
    - Interaction events (tickets, calls, chats) with sentiment analysis
    - Past recommendations with outcome status (Pending/Delivered/Accepted/Declined)

    Args:
        customer_id: Target customer UUID
        months: Number of months of history (1-12, default 12)
        current_user: Authenticated user from Azure AD (injected)
        _: RBAC scope validation (injected)
        customer_service: CustomerService instance (injected)
        recommendation_service: RecommendationService instance (injected)

    Returns:
        CustomerHistoryResponse with interactions and past_recommendations

    Raises:
        HTTPException 404: Customer not found
        HTTPException 401: Unauthorized (no valid Azure AD token)
        HTTPException 400: Invalid months parameter
    """
    with tracer.start_as_current_span("api.get_customer_history") as span:
        span.set_attribute("customer_id", str(customer_id))
        span.set_attribute("months", months)
        span.set_attribute("user_id", current_user.get("oid", "unknown"))

        logger.info(
            f"GET /customers/{customer_id}/history (months={months}) by user {current_user.get('oid')}"
        )

        try:
            # Fetch interactions and past recommendations in parallel
            interactions = await customer_service.get_historical_interactions(
                customer_id, months
            )
            past_recommendations = await recommendation_service.get_past_recommendations(
                customer_id, months
            )

            # Check if customer exists (at least one interaction or recommendation)
            if not interactions and not past_recommendations:
                logger.warning(f"No history found for customer {customer_id}")
                # Note: This could be a new customer with no history yet, not necessarily a 404
                # For now, return empty history instead of 404
                pass

            logger.info(
                f"Retrieved {len(interactions)} interactions and {len(past_recommendations)} recommendations for customer {customer_id}"
            )
            span.set_attribute("interaction_count", len(interactions))
            span.set_attribute("recommendation_count", len(past_recommendations))

            return CustomerHistoryResponse(
                interactions=[InteractionEvent(**i) for i in interactions],
                past_recommendations=[PastRecommendation(**r) for r in past_recommendations],
            )

        except ValueError as e:
            # Invalid months parameter
            logger.error(f"Invalid parameter: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except RuntimeError as e:
            # Service failure
            logger.error(f"Failed to retrieve history: {e}", exc_info=True)
            span.set_attribute("error", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve customer history",
            )
        except Exception as e:
            # Unexpected error
            logger.error(f"Unexpected error: {e}", exc_info=True)
            span.set_attribute("error", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )
