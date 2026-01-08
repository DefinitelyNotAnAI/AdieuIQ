"""
Customer Service - Business logic for customer search and profile retrieval.

This service implements fuzzy search per FR-001, retrieves customer profiles from
Cosmos DB, aggregates usage data from Fabric IQ, and calculates sentiment indicators.

Constitutional Compliance (NON-NEGOTIABLE):
- Uses Managed Identity for Cosmos DB and Fabric IQ access
- Implements fuzzy matching for customer search
- Aggregates usage data from Fabric IQ semantic layer
- Calculates sentiment indicators from interaction history
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from azure.cosmos import ContainerProxy, CosmosClient
from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential
from fuzzywuzzy import fuzz

from ..core.observability import get_tracer
from ..models.customer import Customer
from ..models.interaction_event import InteractionEvent
from .fabric_client import FabricIQClient

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class CustomerService:
    """
    High-level service for customer search and profile retrieval.

    Responsibilities:
    - Search customers with fuzzy matching (FR-001)
    - Retrieve customer profile from Cosmos DB
    - Aggregate usage data from Fabric IQ
    - Calculate sentiment indicators from interaction history
    - Build composite CustomerProfile for API responses
    """

    def __init__(self, credential: TokenCredential | None = None):
        """
        Initialize service with Cosmos DB and Fabric IQ clients.

        Args:
            credential: Azure credential for authentication (optional, uses DefaultAzureCredential if None)
        """
        self.credential = credential or DefaultAzureCredential()
        self.fabric_client = FabricIQClient()

        # Initialize Cosmos DB client
        if os.getenv("ENV") == "local":
            logger.info("CustomerService running in local mock mode")
            self.cosmos_client = None
            self.customers_container = None
            self.interactions_container = None
        else:
            cosmos_endpoint = os.getenv("COSMOS_DB_ENDPOINT")
            if not cosmos_endpoint:
                raise ValueError("COSMOS_DB_ENDPOINT environment variable not set")

            self.cosmos_client = CosmosClient(
                url=cosmos_endpoint, credential=self.credential
            )
            database = self.cosmos_client.get_database_client("adieuiq")
            self.customers_container: ContainerProxy = database.get_container_client(
                "customers"
            )
            self.interactions_container: ContainerProxy = (
                database.get_container_client("interaction-events")
            )

        logger.info("CustomerService initialized")

    async def search_customers(
        self, query: str, limit: int = 20, min_score: int = 60
    ) -> list[dict[str, Any]]:
        """
        Search customers with fuzzy matching per FR-001.

        Uses fuzzywuzzy library for fuzzy string matching on company_name.
        Returns customers sorted by match score descending.

        Args:
            query: Search query string (company name)
            limit: Maximum number of results (default 20)
            min_score: Minimum fuzzy match score 0-100 (default 60)

        Returns:
            List of customer dictionaries with match_score field
        """
        with tracer.start_as_current_span("customer_service.search") as span:
            span.set_attribute("query", query)
            span.set_attribute("limit", limit)

            if os.getenv("ENV") == "local":
                # Mock mode: return sample customers
                return await self._get_mock_customers(query)

            try:
                # Query all customers (use caching or secondary index in production)
                # TODO: Consider using Azure Cognitive Search for better performance at scale
                all_customers = list(
                    self.customers_container.query_items(
                        query="SELECT * FROM c", enable_cross_partition_query=True
                    )
                )

                # Calculate fuzzy match scores
                scored_customers = []
                for customer in all_customers:
                    company_name = customer.get("company_name", "")
                    # Use partial_ratio for substring matching
                    score = fuzz.partial_ratio(query.lower(), company_name.lower())

                    if score >= min_score:
                        customer["match_score"] = score
                        scored_customers.append(customer)

                # Sort by score descending
                scored_customers.sort(key=lambda x: x["match_score"], reverse=True)

                # Limit results
                results = scored_customers[:limit]

                logger.info(
                    f"Customer search for '{query}' returned {len(results)} results"
                )
                span.set_attribute("result_count", len(results))

                return results

            except Exception as e:
                logger.error(f"Customer search failed: {e}", exc_info=True)
                span.set_attribute("error", str(e))
                return []

    async def get_customer_profile(
        self, customer_id: UUID, include_usage: bool = True, include_sentiment: bool = True
    ) -> dict[str, Any] | None:
        """
        Retrieve comprehensive customer profile.

        Builds composite CustomerProfile per contracts/openapi.yaml:
        - Customer entity from Cosmos DB
        - Usage summary from Fabric IQ (if include_usage=True)
        - Sentiment indicators from interaction history (if include_sentiment=True)

        Args:
            customer_id: Target customer identifier
            include_usage: Whether to fetch usage data from Fabric IQ (default True)
            include_sentiment: Whether to calculate sentiment indicators (default True)

        Returns:
            CustomerProfile dictionary or None if customer not found
        """
        with tracer.start_as_current_span("customer_service.get_profile") as span:
            span.set_attribute("customer_id", str(customer_id))
            span.set_attribute("include_usage", include_usage)
            span.set_attribute("include_sentiment", include_sentiment)

            if os.getenv("ENV") == "local":
                # Mock mode: return sample profile
                return await self._get_mock_profile(customer_id)

            try:
                # Fetch customer entity
                customer = await self._get_customer_by_id(customer_id)
                if not customer:
                    logger.warning(f"Customer {customer_id} not found")
                    span.set_attribute("found", False)
                    return None

                profile = {
                    "customer": customer,
                    "usage_summary": None,
                    "sentiment_indicators": None,
                }

                # Fetch usage summary from Fabric IQ
                if include_usage:
                    usage_summary = await self._get_usage_summary(customer_id)
                    profile["usage_summary"] = usage_summary

                # Calculate sentiment indicators
                if include_sentiment:
                    sentiment_indicators = await self._get_sentiment_indicators(
                        customer_id
                    )
                    profile["sentiment_indicators"] = sentiment_indicators

                logger.info(f"Retrieved customer profile for {customer_id}")
                span.set_attribute("found", True)

                return profile

            except Exception as e:
                logger.error(f"Failed to retrieve customer profile: {e}", exc_info=True)
                span.set_attribute("error", str(e))
                return None

    async def _get_customer_by_id(self, customer_id: UUID) -> dict[str, Any] | None:
        """
        Retrieve customer entity from Cosmos DB.

        Args:
            customer_id: Target customer identifier

        Returns:
            Customer dictionary or None if not found
        """
        try:
            query = "SELECT * FROM c WHERE c.account_id = @account_id"
            items = list(
                self.customers_container.query_items(
                    query=query,
                    parameters=[{"name": "@account_id", "value": str(customer_id)}],
                    enable_cross_partition_query=True,
                )
            )

            if not items:
                return None

            return items[0]

        except Exception as e:
            logger.error(f"Failed to retrieve customer from Cosmos DB: {e}", exc_info=True)
            return None

    async def _get_usage_summary(self, customer_id: UUID) -> dict[str, Any]:
        """
        Aggregate usage data from Fabric IQ.

        Args:
            customer_id: Target customer identifier

        Returns:
            Usage summary with feature breakdown and intensity scores
        """
        try:
            # Query Fabric IQ for usage trends (past 90 days)
            usage_data = await self.fabric_client.get_usage_trends(
                customer_id=customer_id, days=90
            )

            # Aggregate by intensity
            high_usage_features = [
                u["feature_name"]
                for u in usage_data
                if u["intensity_score"] == "High"
            ]
            medium_usage_features = [
                u["feature_name"]
                for u in usage_data
                if u["intensity_score"] == "Medium"
            ]
            low_usage_features = [
                u["feature_name"] for u in usage_data if u["intensity_score"] == "Low"
            ]
            unused_features = [
                u["feature_name"]
                for u in usage_data
                if u["intensity_score"] == "None"
            ]

            return {
                "total_features_available": len(usage_data),
                "high_usage_features": high_usage_features,
                "medium_usage_features": medium_usage_features,
                "low_usage_features": low_usage_features,
                "unused_features": unused_features,
                "adoption_rate": len(high_usage_features + medium_usage_features)
                / len(usage_data)
                if usage_data
                else 0.0,
                "last_updated": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to aggregate usage summary: {e}", exc_info=True)
            return {
                "total_features_available": 0,
                "high_usage_features": [],
                "medium_usage_features": [],
                "low_usage_features": [],
                "unused_features": [],
                "adoption_rate": 0.0,
                "last_updated": datetime.utcnow().isoformat(),
                "error": str(e),
            }

    async def _get_sentiment_indicators(self, customer_id: UUID) -> dict[str, Any]:
        """
        Calculate sentiment indicators from interaction history.

        Args:
            customer_id: Target customer identifier

        Returns:
            Sentiment indicators with overall score, trend, and recent issues
        """
        try:
            # Query interaction events from past 90 days
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            query = """
                SELECT * FROM c 
                WHERE c.customer_id = @customer_id 
                AND c.timestamp >= @cutoff_date
                ORDER BY c.timestamp DESC
            """

            items = list(
                self.interactions_container.query_items(
                    query=query,
                    parameters=[
                        {"name": "@customer_id", "value": str(customer_id)},
                        {"name": "@cutoff_date", "value": cutoff_date.isoformat()},
                    ],
                    partition_key=str(customer_id),
                )
            )

            if not items:
                return {
                    "overall_sentiment_score": 0.0,
                    "sentiment_trend": "neutral",
                    "recent_issues_count": 0,
                    "unresolved_issues_count": 0,
                    "interaction_count": 0,
                    "last_updated": datetime.utcnow().isoformat(),
                }

            # Calculate overall sentiment (exponential decay weighting for recency)
            weighted_sum = 0.0
            weight_sum = 0.0
            for i, interaction in enumerate(items):
                weight = 0.9**i  # Exponential decay
                sentiment = interaction.get("sentiment_score", 0.0)
                weighted_sum += sentiment * weight
                weight_sum += weight

            overall_sentiment = weighted_sum / weight_sum if weight_sum > 0 else 0.0

            # Determine trend (compare first 30 days vs last 30 days)
            recent_sentiments = [
                i["sentiment_score"]
                for i in items[:30]
                if "sentiment_score" in i
            ]
            older_sentiments = [
                i["sentiment_score"]
                for i in items[30:60]
                if "sentiment_score" in i
            ]

            recent_avg = (
                sum(recent_sentiments) / len(recent_sentiments)
                if recent_sentiments
                else 0.0
            )
            older_avg = (
                sum(older_sentiments) / len(older_sentiments) if older_sentiments else 0.0
            )

            if recent_avg > older_avg + 0.1:
                trend = "improving"
            elif recent_avg < older_avg - 0.1:
                trend = "declining"
            else:
                trend = "stable"

            # Count unresolved issues
            unresolved = [
                i
                for i in items
                if i.get("resolution_status") in ["Pending", "Escalated"]
            ]
            recent_issues = [
                i
                for i in items[:10]
                if i.get("resolution_status") in ["Pending", "Escalated"]
            ]

            return {
                "overall_sentiment_score": round(overall_sentiment, 3),
                "sentiment_trend": trend,
                "recent_issues_count": len(recent_issues),
                "unresolved_issues_count": len(unresolved),
                "interaction_count": len(items),
                "last_updated": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to calculate sentiment indicators: {e}", exc_info=True)
            return {
                "overall_sentiment_score": 0.0,
                "sentiment_trend": "neutral",
                "recent_issues_count": 0,
                "unresolved_issues_count": 0,
                "interaction_count": 0,
                "last_updated": datetime.utcnow().isoformat(),
                "error": str(e),
            }

    async def _get_mock_customers(self, query: str) -> list[dict[str, Any]]:
        """
        Return mock customers for local development.

        Args:
            query: Search query string

        Returns:
            List of mock customer dictionaries
        """
        mock_customers = [
            {
                "account_id": "550e8400-e29b-41d4-a716-446655440001",
                "company_name": "Acme Corporation",
                "industry_segment": "Technology",
                "product_tier": "Enterprise",
                "subscription_start_date": "2024-01-15T00:00:00Z",
                "current_products": ["Product A", "Product B", "Product C"],
                "contact_email": "contact@acme.example.com",
                "match_score": 85,
            },
            {
                "account_id": "550e8400-e29b-41d4-a716-446655440002",
                "company_name": "TechVentures Inc",
                "industry_segment": "Technology",
                "product_tier": "Professional",
                "subscription_start_date": "2024-03-20T00:00:00Z",
                "current_products": ["Product A", "Product B"],
                "contact_email": "admin@techventures.example.com",
                "match_score": 75,
            },
            {
                "account_id": "550e8400-e29b-41d4-a716-446655440003",
                "company_name": "Global Health Systems",
                "industry_segment": "Healthcare",
                "product_tier": "Enterprise",
                "subscription_start_date": "2023-11-01T00:00:00Z",
                "current_products": ["Product A", "Product C"],
                "contact_email": "it@globalhealth.example.com",
                "match_score": 70,
            },
        ]

        # Filter by query if provided
        if query:
            filtered = [
                c
                for c in mock_customers
                if query.lower() in c["company_name"].lower()
            ]
            logger.info(
                f"Mock mode: customer search for '{query}' returned {len(filtered)} results"
            )
            return filtered

        logger.info(f"Mock mode: returning {len(mock_customers)} sample customers")
        return mock_customers

    async def _get_mock_profile(self, customer_id: UUID) -> dict[str, Any]:
        """
        Return mock customer profile for local development.

        Args:
            customer_id: Target customer identifier

        Returns:
            Mock CustomerProfile dictionary
        """
        return {
            "customer": {
                "account_id": str(customer_id),
                "company_name": "Acme Corporation",
                "industry_segment": "Technology",
                "product_tier": "Enterprise",
                "subscription_start_date": "2024-01-15T00:00:00Z",
                "current_products": ["Product A", "Product B", "Product C"],
                "contact_email": "contact@acme.example.com",
            },
            "usage_summary": {
                "total_features_available": 5,
                "high_usage_features": ["Dashboard Analytics"],
                "medium_usage_features": ["API Integration", "Custom Workflows"],
                "low_usage_features": ["Data Export"],
                "unused_features": ["Advanced Reporting"],
                "adoption_rate": 0.6,
                "last_updated": datetime.utcnow().isoformat(),
            },
            "sentiment_indicators": {
                "overall_sentiment_score": 0.45,
                "sentiment_trend": "improving",
                "recent_issues_count": 1,
                "unresolved_issues_count": 1,
                "interaction_count": 8,
                "last_updated": datetime.utcnow().isoformat(),
            },
        }
