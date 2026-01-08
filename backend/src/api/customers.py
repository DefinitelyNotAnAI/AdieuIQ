"""
Customer API endpoints.

Implements customer search and profile retrieval endpoints per contracts/openapi.yaml.

Constitutional Compliance (NON-NEGOTIABLE):
- Azure AD authentication required for all endpoints
- RBAC enforcement (api://adieuiq/Customers.Read scope)
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

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

router = APIRouter(prefix="/customers", tags=["Customers"])


# Response Models (per OpenAPI spec)
class CustomerSearchResult(BaseModel):
    """Customer search result with match score."""

    account_id: str = Field(..., description="Customer UUID")
    company_name: str = Field(..., max_length=200)
    industry_segment: str
    product_tier: str
    subscription_start_date: str
    current_products: list[str]
    contact_email: str | None = None
    match_score: int = Field(..., ge=0, le=100, description="Fuzzy match score 0-100")


class UsageSummary(BaseModel):
    """Usage data summary."""

    total_features_available: int
    high_usage_features: list[str]
    medium_usage_features: list[str]
    low_usage_features: list[str]
    unused_features: list[str]
    adoption_rate: float = Field(..., ge=0.0, le=1.0)
    last_updated: str


class SentimentIndicators(BaseModel):
    """Sentiment analysis indicators."""

    overall_sentiment_score: float = Field(..., ge=-1.0, le=1.0)
    sentiment_trend: str = Field(..., description="improving, declining, or stable")
    recent_issues_count: int = Field(..., ge=0)
    unresolved_issues_count: int = Field(..., ge=0)
    interaction_count: int = Field(..., ge=0)
    last_updated: str


class CustomerProfile(BaseModel):
    """Composite customer profile (per OpenAPI spec)."""

    customer: dict[str, Any]
    usage_summary: UsageSummary | None
    sentiment_indicators: SentimentIndicators | None


@router.get(
    "/search",
    response_model=list[CustomerSearchResult],
    summary="Search for customers",
    description="Search customers with fuzzy matching per FR-001. Requires Customers.Read scope.",
)
async def search_customers(
    query: str = Query(..., min_length=1, description="Search query (company name)"),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
    min_score: int = Query(60, ge=0, le=100, description="Minimum fuzzy match score"),
    current_user: dict = Depends(get_current_user),
    _scope_check: None = Depends(require_scope("api://adieuiq/Customers.Read")),
) -> list[CustomerSearchResult]:
    """
    Search for customers with fuzzy matching (T035).

    Implements FR-001: Fuzzy search on company name with configurable threshold.

    Args:
        query: Search query string
        limit: Maximum number of results (default 20, max 100)
        min_score: Minimum fuzzy match score 0-100 (default 60)
        current_user: Authenticated user from Azure AD token
        _scope_check: RBAC scope validation

    Returns:
        List of matching customers with match scores

    Raises:
        HTTPException: 401 if unauthorized, 500 if search fails
    """
    with tracer.start_as_current_span("api.customers.search") as span:
        span.set_attribute("query", query)
        span.set_attribute("limit", limit)
        span.set_attribute("user_id", current_user.get("sub"))

        try:
            customer_service = CustomerService()
            results = await customer_service.search_customers(
                query=query, limit=limit, min_score=min_score
            )

            logger.info(
                f"Customer search for '{query}' returned {len(results)} results (user: {current_user.get('sub')})"
            )
            span.set_attribute("result_count", len(results))

            # Convert to response model
            return [CustomerSearchResult(**result) for result in results]

        except Exception as e:
            logger.error(f"Customer search failed: {e}", exc_info=True)
            span.set_attribute("error", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Customer search failed: {str(e)}",
            )


@router.get(
    "/{customer_id}/profile",
    response_model=CustomerProfile,
    summary="Get customer profile",
    description="Retrieve comprehensive customer profile with usage and sentiment. Requires Customers.Read scope.",
)
async def get_customer_profile(
    customer_id: UUID,
    include_usage: bool = Query(True, description="Include usage summary from Fabric IQ"),
    include_sentiment: bool = Query(
        True, description="Include sentiment indicators from interaction history"
    ),
    current_user: dict = Depends(get_current_user),
    _scope_check: None = Depends(require_scope("api://adieuiq/Customers.Read")),
) -> CustomerProfile:
    """
    Get comprehensive customer profile (T036).

    Builds composite CustomerProfile per contracts/openapi.yaml:
    - Customer entity from Cosmos DB
    - Usage summary from Fabric IQ (optional)
    - Sentiment indicators from interaction history (optional)

    Args:
        customer_id: Target customer UUID
        include_usage: Whether to fetch usage data (default True)
        include_sentiment: Whether to calculate sentiment (default True)
        current_user: Authenticated user from Azure AD token
        _scope_check: RBAC scope validation

    Returns:
        CustomerProfile with customer, usage_summary, sentiment_indicators

    Raises:
        HTTPException: 404 if customer not found, 500 if retrieval fails
    """
    with tracer.start_as_current_span("api.customers.get_profile") as span:
        span.set_attribute("customer_id", str(customer_id))
        span.set_attribute("include_usage", include_usage)
        span.set_attribute("include_sentiment", include_sentiment)
        span.set_attribute("user_id", current_user.get("sub"))

        try:
            customer_service = CustomerService()
            profile = await customer_service.get_customer_profile(
                customer_id=customer_id,
                include_usage=include_usage,
                include_sentiment=include_sentiment,
            )

            if not profile:
                logger.warning(f"Customer {customer_id} not found")
                span.set_attribute("found", False)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Customer {customer_id} not found",
                )

            logger.info(
                f"Retrieved customer profile for {customer_id} (user: {current_user.get('sub')})"
            )
            span.set_attribute("found", True)

            # Convert to response model
            return CustomerProfile(
                customer=profile["customer"],
                usage_summary=UsageSummary(**profile["usage_summary"])
                if profile.get("usage_summary")
                else None,
                sentiment_indicators=SentimentIndicators(**profile["sentiment_indicators"])
                if profile.get("sentiment_indicators")
                else None,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve customer profile: {e}", exc_info=True)
            span.set_attribute("error", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve customer profile: {str(e)}",
            )
