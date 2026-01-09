"""
Recommendation Service - High-level business logic for recommendation generation.

This service orchestrates the multi-agent workflow, manages caching in Cosmos DB,
and handles graceful degradation per FR-017.

Constitutional Compliance (NON-NEGOTIABLE):
- Uses RecommendationOrchestrator (Azure AI Foundry SDK patterns)
- Caches recommendations in Cosmos DB for 12-month retention
- Implements graceful degradation when orchestration fails
- Enforces Content Safety validation (Constitutional Principle III)
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from azure.cosmos import ContainerProxy, CosmosClient
from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential

from ..core.observability import get_tracer
from ..models.recommendation import OutcomeStatus, Recommendation
from .orchestration.orchestrator import RecommendationOrchestrator

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class RecommendationService:
    """
    High-level service for recommendation generation and retrieval.

    Responsibilities:
    - Orchestrate multi-agent recommendation generation
    - Cache recommendations in Cosmos DB
    - Retrieve historical recommendations
    - Update recommendation outcomes (Delivered/Accepted/Declined)
    - Handle graceful degradation per FR-017
    """

    def __init__(self, credential: TokenCredential | None = None):
        """
        Initialize service with Cosmos DB client and orchestrator.

        Args:
            credential: Azure credential for authentication (optional, uses DefaultAzureCredential if None)
        """
        self.credential = credential or DefaultAzureCredential()
        self.orchestrator = RecommendationOrchestrator(credential=self.credential)

        # Initialize Cosmos DB client
        if os.getenv("ENV") == "local":
            logger.info("RecommendationService running in local mock mode")
            self.cosmos_client = None
            self.recommendations_container = None
        else:
            cosmos_endpoint = os.getenv("COSMOS_DB_ENDPOINT")
            if not cosmos_endpoint:
                raise ValueError("COSMOS_DB_ENDPOINT environment variable not set")

            self.cosmos_client = CosmosClient(
                url=cosmos_endpoint, credential=self.credential
            )
            database = self.cosmos_client.get_database_client("adieuiq")
            self.recommendations_container: ContainerProxy = (
                database.get_container_client("recommendations")
            )

        logger.info("RecommendationService initialized")

    async def generate_recommendations(
        self, customer_id: UUID, force_refresh: bool = False
    ) -> dict[str, Any]:
        """
        Generate new recommendations for a customer.

        Checks cache first unless force_refresh=True, then orchestrates agents
        to generate fresh recommendations. Caches results in Cosmos DB with 12-month TTL.

        Args:
            customer_id: Target customer identifier
            force_refresh: If True, bypass cache and regenerate (default False)

        Returns:
            Dictionary containing:
            - adoption_recommendations: List of validated adoption recommendations
            - upsell_recommendations: List of validated upsell recommendations
            - cached: Boolean indicating if results were from cache
            - generation_time_ms: Total time (includes cache lookup or generation)
            - orchestration_metadata: Metadata from orchestrator

        Raises:
            ValueError: If customer_id is invalid
            RuntimeError: If generation fails and graceful degradation is not possible
        """
        with tracer.start_as_current_span("recommendation_service.generate") as span:
            span.set_attribute("customer_id", str(customer_id))
            span.set_attribute("force_refresh", force_refresh)

            start_time = datetime.now()

            # Check cache first (unless force_refresh)
            if not force_refresh:
                cached_result = await self._get_cached_recommendations(customer_id)
                if cached_result:
                    end_time = datetime.now()
                    generation_time_ms = int(
                        (end_time - start_time).total_seconds() * 1000
                    )

                    logger.info(
                        f"Returning cached recommendations for customer {customer_id}"
                    )
                    span.set_attribute("cache_hit", True)

                    return {
                        **cached_result,
                        "cached": True,
                        "generation_time_ms": generation_time_ms,
                    }

            span.set_attribute("cache_hit", False)

            try:
                # Fetch past recommendations for duplicate detection (US3/T057)
                logger.info(f"Fetching past recommendations for customer {customer_id} (for duplicate detection)")
                past_recommendations = await self.get_past_recommendations(customer_id, months=12)
                logger.info(f"Found {len(past_recommendations)} past recommendations for duplicate detection")

                # Generate fresh recommendations via orchestrator (pass past_recommendations for FR-014)
                logger.info(f"Generating fresh recommendations for customer {customer_id}")
                result = await self.orchestrator.generate_recommendations(
                    customer_id, past_recommendations=past_recommendations
                )

                # Cache results in Cosmos DB (12-month TTL per data-model.md)
                await self._cache_recommendations(customer_id, result)

                end_time = datetime.now()
                generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

                return {
                    **result,
                    "cached": False,
                    "generation_time_ms": generation_time_ms,
                }

            except Exception as e:
                logger.error(
                    f"RecommendationService.generate_recommendations failed: {e}",
                    exc_info=True,
                )
                span.set_attribute("error", str(e))
                span.set_attribute("success", False)

                # Graceful degradation per FR-017
                return await self._graceful_degradation_result(customer_id, str(e))

    async def get_recommendations_by_customer(
        self,
        customer_id: UUID,
        outcome_status: OutcomeStatus | None = None,
        months: int = 12,
    ) -> list[Recommendation]:
        """
        Retrieve historical recommendations for a customer.

        Args:
            customer_id: Target customer identifier
            outcome_status: Optional filter by outcome status (Pending, Delivered, Accepted, Declined)
            months: Number of months to look back (default 12)

        Returns:
            List of Recommendation objects sorted by generation_timestamp descending
        """
        with tracer.start_as_current_span("recommendation_service.get_by_customer") as span:
            span.set_attribute("customer_id", str(customer_id))
            span.set_attribute("months", months)

            if os.getenv("ENV") == "local":
                # Mock mode: return empty list
                logger.info(
                    f"Mock mode: returning empty historical recommendations for customer {customer_id}"
                )
                return []

            try:
                # Query Cosmos DB with partition key optimization
                cutoff_date = datetime.utcnow() - timedelta(days=months * 30)
                query = """
                    SELECT * FROM c 
                    WHERE c.customer_id = @customer_id 
                    AND c.generation_timestamp >= @cutoff_date
                """

                parameters = [
                    {"name": "@customer_id", "value": str(customer_id)},
                    {"name": "@cutoff_date", "value": cutoff_date.isoformat()},
                ]

                if outcome_status:
                    query += " AND c.outcome_status = @outcome_status"
                    parameters.append(
                        {"name": "@outcome_status", "value": outcome_status.value}
                    )

                query += " ORDER BY c.generation_timestamp DESC"

                items = list(
                    self.recommendations_container.query_items(
                        query=query,
                        parameters=parameters,
                        partition_key=str(customer_id),
                    )
                )

                recommendations = [Recommendation(**item) for item in items]

                logger.info(
                    f"Retrieved {len(recommendations)} historical recommendations for customer {customer_id}"
                )
                span.set_attribute("recommendation_count", len(recommendations))

                return recommendations

            except Exception as e:
                logger.error(
                    f"Failed to retrieve historical recommendations: {e}", exc_info=True
                )
                span.set_attribute("error", str(e))
                return []

    async def update_recommendation_outcome(
        self,
        recommendation_id: UUID,
        outcome_status: OutcomeStatus,
        agent_id: str,
        feedback: str | None = None,
    ) -> bool:
        """
        Update recommendation outcome (Delivered/Accepted/Declined).

        Implements audit trail per FR-020 by tracking agent_id and timestamp.

        Args:
            recommendation_id: Recommendation to update
            outcome_status: New outcome status
            agent_id: Support agent performing the update
            feedback: Optional feedback text from agent or customer

        Returns:
            True if update succeeded, False otherwise
        """
        with tracer.start_as_current_span("recommendation_service.update_outcome") as span:
            span.set_attribute("recommendation_id", str(recommendation_id))
            span.set_attribute("outcome_status", outcome_status.value)
            span.set_attribute("agent_id", agent_id)

            if os.getenv("ENV") == "local":
                # Mock mode: always succeed
                logger.info(
                    f"Mock mode: updated recommendation {recommendation_id} to {outcome_status.value}"
                )
                return True

            try:
                # Retrieve recommendation to get customer_id (partition key)
                query = "SELECT * FROM c WHERE c.recommendation_id = @recommendation_id"
                items = list(
                    self.recommendations_container.query_items(
                        query=query,
                        parameters=[
                            {"name": "@recommendation_id", "value": str(recommendation_id)}
                        ],
                    )
                )

                if not items:
                    logger.warning(f"Recommendation {recommendation_id} not found")
                    span.set_attribute("found", False)
                    return False

                recommendation = items[0]
                customer_id = recommendation["customer_id"]

                # Update outcome fields
                recommendation["outcome_status"] = outcome_status.value
                recommendation["delivered_by_agent_id"] = agent_id
                recommendation["outcome_timestamp"] = datetime.utcnow().isoformat()
                recommendation["updated_at"] = datetime.utcnow().isoformat()

                if feedback:
                    recommendation["feedback"] = feedback

                # Upsert back to Cosmos DB
                self.recommendations_container.upsert_item(
                    body=recommendation, partition_key=customer_id
                )

                logger.info(
                    f"Updated recommendation {recommendation_id} to {outcome_status.value}"
                )
                span.set_attribute("success", True)

                return True

            except Exception as e:
                logger.error(f"Failed to update recommendation outcome: {e}", exc_info=True)
                span.set_attribute("error", str(e))
                span.set_attribute("success", False)
                return False

    async def _get_cached_recommendations(self, customer_id: UUID) -> dict[str, Any] | None:
        """
        Retrieve recent cached recommendations from Cosmos DB.

        Returns recommendations generated within the last 24 hours to avoid
        re-generating unnecessarily.

        Args:
            customer_id: Target customer identifier

        Returns:
            Cached result dict or None if no recent cache exists
        """
        if os.getenv("ENV") == "local":
            # Mock mode: no cache
            return None

        try:
            # Query for recommendations generated in last 24 hours with outcome_status=Pending
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            query = """
                SELECT * FROM c 
                WHERE c.customer_id = @customer_id 
                AND c.generation_timestamp >= @cutoff_time
                AND c.outcome_status = 'Pending'
                ORDER BY c.generation_timestamp DESC
            """

            items = list(
                self.recommendations_container.query_items(
                    query=query,
                    parameters=[
                        {"name": "@customer_id", "value": str(customer_id)},
                        {"name": "@cutoff_time", "value": cutoff_time.isoformat()},
                    ],
                    partition_key=str(customer_id),
                )
            )

            if not items:
                return None

            # Group recommendations by type
            adoption_recs = [r for r in items if r["recommendation_type"] == "Adoption"]
            upsell_recs = [r for r in items if r["recommendation_type"] == "Upsell"]

            logger.info(
                f"Cache hit: {len(adoption_recs)} adoption + {len(upsell_recs)} upsell for customer {customer_id}"
            )

            return {
                "adoption_recommendations": adoption_recs,
                "upsell_recommendations": upsell_recs,
                "orchestration_metadata": {
                    "customer_id": str(customer_id),
                    "cache_source": "cosmos_db",
                    "cached_at": items[0]["generation_timestamp"],
                },
            }

        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}", exc_info=True)
            return None

    async def _cache_recommendations(
        self, customer_id: UUID, result: dict[str, Any]
    ) -> None:
        """
        Cache generated recommendations in Cosmos DB.

        Args:
            customer_id: Target customer identifier
            result: Orchestrator result with recommendations and metadata
        """
        if os.getenv("ENV") == "local":
            # Mock mode: skip caching
            return

        try:
            adoption_recs = result.get("adoption_recommendations", [])
            upsell_recs = result.get("upsell_recommendations", [])

            all_recommendations = adoption_recs + upsell_recs

            for rec in all_recommendations:
                # Add system fields
                rec["customer_id"] = str(customer_id)
                rec["generation_timestamp"] = datetime.utcnow().isoformat()
                rec["outcome_status"] = OutcomeStatus.PENDING.value
                rec["created_at"] = datetime.utcnow().isoformat()
                rec["updated_at"] = datetime.utcnow().isoformat()

                # Set 12-month TTL (in seconds)
                rec["ttl"] = 365 * 24 * 60 * 60  # 12 months

                # Upsert to Cosmos DB
                self.recommendations_container.upsert_item(
                    body=rec, partition_key=str(customer_id)
                )

            logger.info(
                f"Cached {len(all_recommendations)} recommendations for customer {customer_id}"
            )

        except Exception as e:
            # Non-critical failure: log warning but don't fail the request
            logger.warning(f"Failed to cache recommendations: {e}", exc_info=True)

    async def get_past_recommendations(
        self, customer_id: UUID, months: int = 12
    ) -> list[dict[str, Any]]:
        """
        Retrieve past 12 months of Recommendations with outcomes.

        Returns recommendations sorted chronologically (most recent first).
        Per FR-013, supports retrieving up to 12 months of history.

        Args:
            customer_id: Target customer identifier
            months: Number of months of history (1-12, default 12)

        Returns:
            List of Recommendation dictionaries with outcomes, sorted by generation_timestamp descending

        Raises:
            ValueError: If months is not in range 1-12
        """
        if not 1 <= months <= 12:
            raise ValueError("months must be between 1 and 12")

        with tracer.start_as_current_span("recommendation_service.get_past_recommendations") as span:
            span.set_attribute("customer_id", str(customer_id))
            span.set_attribute("months", months)

            # Mock mode for local development
            if os.getenv("ENV") == "local":
                logger.info(f"Mock mode: returning mock past recommendations for customer {customer_id}")
                return await self._get_mock_past_recommendations(customer_id, months)

            try:
                # Calculate time window
                cutoff_date = datetime.utcnow() - timedelta(days=months * 30)
                
                # Query Cosmos DB for recommendations within time window
                query = """
                    SELECT * FROM c 
                    WHERE c.customer_id = @customer_id 
                    AND c.generation_timestamp >= @cutoff_date
                    ORDER BY c.generation_timestamp DESC
                """
                parameters = [
                    {"name": "@customer_id", "value": str(customer_id)},
                    {"name": "@cutoff_date", "value": cutoff_date.isoformat()}
                ]

                recommendations = list(
                    self.recommendations_container.query_items(
                        query=query,
                        parameters=parameters,
                        partition_key=str(customer_id)
                    )
                )

                logger.info(f"Retrieved {len(recommendations)} past recommendations for customer {customer_id}")
                span.set_attribute("recommendation_count", len(recommendations))
                
                return recommendations

            except Exception as e:
                logger.error(f"Failed to retrieve past recommendations for customer {customer_id}: {e}", exc_info=True)
                span.set_attribute("error", str(e))
                raise RuntimeError(f"Failed to retrieve past recommendations: {e}") from e

    async def _get_mock_past_recommendations(self, customer_id: UUID, months: int) -> list[dict[str, Any]]:
        """
        Return mock past recommendations for local development.

        Args:
            customer_id: Target customer identifier
            months: Number of months of history

        Returns:
            List of mock Recommendation dictionaries
        """
        now = datetime.utcnow()
        mock_recommendations = [
            {
                "recommendation_id": "rec-001",
                "customer_id": str(customer_id),
                "recommendation_type": "Adoption",
                "recommendation_text": "Enable Advanced Reporting feature for better insights",
                "confidence_score": 0.85,
                "reasoning_chain": {
                    "retrieval": "Customer has high usage of Dashboard Analytics",
                    "sentiment": "Positive sentiment, no recent issues",
                    "reasoning": "Advanced Reporting complements current dashboard usage"
                },
                "generation_timestamp": (now - timedelta(days=10)).isoformat(),
                "outcome_status": "Accepted",
                "delivered_by_agent_id": "agent-123",
                "outcome_timestamp": (now - timedelta(days=8)).isoformat()
            },
            {
                "recommendation_id": "rec-002",
                "customer_id": str(customer_id),
                "recommendation_type": "Upsell",
                "recommendation_text": "Upgrade to Enterprise Plus tier for advanced security features",
                "confidence_score": 0.72,
                "reasoning_chain": {
                    "retrieval": "Customer inquired about enterprise features",
                    "sentiment": "Positive engagement with sales team",
                    "reasoning": "Enterprise Plus provides security enhancements"
                },
                "generation_timestamp": (now - timedelta(days=25)).isoformat(),
                "outcome_status": "Declined",
                "delivered_by_agent_id": "agent-456",
                "outcome_timestamp": (now - timedelta(days=23)).isoformat()
            },
            {
                "recommendation_id": "rec-003",
                "customer_id": str(customer_id),
                "recommendation_type": "Adoption",
                "recommendation_text": "Try the new Custom Workflows feature for automation",
                "confidence_score": 0.78,
                "reasoning_chain": {
                    "retrieval": "Customer has medium usage of API Integration",
                    "sentiment": "Improving sentiment trend",
                    "reasoning": "Custom Workflows can automate API-based tasks"
                },
                "generation_timestamp": (now - timedelta(days=45)).isoformat(),
                "outcome_status": "Delivered",
                "delivered_by_agent_id": "agent-789",
                "outcome_timestamp": (now - timedelta(days=44)).isoformat()
            },
            {
                "recommendation_id": "rec-004",
                "customer_id": str(customer_id),
                "recommendation_type": "Adoption",
                "recommendation_text": "Enable Data Export feature for reporting needs",
                "confidence_score": 0.68,
                "reasoning_chain": {
                    "retrieval": "Customer has low usage of Data Export",
                    "sentiment": "Previous performance issues resolved",
                    "reasoning": "Data Export complements existing workflows"
                },
                "generation_timestamp": (now - timedelta(days=70)).isoformat(),
                "outcome_status": "Pending",
                "delivered_by_agent_id": None,
                "outcome_timestamp": None
            }
        ]

        # Filter by months
        cutoff_date = now - timedelta(days=months * 30)
        filtered = [
            r for r in mock_recommendations
            if datetime.fromisoformat(r["generation_timestamp"]) >= cutoff_date
        ]

        logger.info(f"Mock mode: returning {len(filtered)} past recommendations for customer {customer_id}")
        return filtered

    async def get_recommendation_explainability(
        self, recommendation_id: UUID
    ) -> dict[str, Any]:
        """
        Retrieve recommendation with agent contributions for explainability (T060).

        Returns full reasoning chain with all agent contributions:
        - Retrieval Agent: Data sources and retrieval confidence
        - Sentiment Agent: Sentiment analysis and factors
        - Reasoning Agent: Candidate generation logic
        - Validation Agent: Filtering and validation results

        Args:
            recommendation_id: Target recommendation identifier

        Returns:
            Dictionary with recommendation and agent_contributions array

        Raises:
            RuntimeError: If retrieval fails
        """
        with tracer.start_as_current_span("recommendation_service.get_explainability") as span:
            span.set_attribute("recommendation_id", str(recommendation_id))

            try:
                # Fetch recommendation from Cosmos DB
                recommendation = await self.get_recommendation_by_id(recommendation_id)
                if not recommendation:
                    logger.warning(f"Recommendation {recommendation_id} not found")
                    return None

                # Fetch agent contributions from orchestrator
                agent_contributions = await self.orchestrator.get_agent_contributions(
                    recommendation_id
                )

                logger.info(
                    f"Retrieved explainability for recommendation {recommendation_id}: "
                    f"{len(agent_contributions)} agent contributions"
                )
                span.set_attribute("contribution_count", len(agent_contributions))

                return {
                    "recommendation": recommendation,
                    "agent_contributions": [
                        {
                            "contribution_id": str(c.contribution_id),
                            "agent_type": c.agent_type.value,
                            "input_data": c.input_data,
                            "output_result": c.output_result,
                            "confidence_score": c.confidence_score,
                            "execution_time_ms": c.execution_time_ms,
                            "created_at": c.created_at.isoformat()
                        }
                        for c in agent_contributions
                    ]
                }

            except Exception as e:
                logger.error(
                    f"Failed to retrieve explainability for recommendation {recommendation_id}: {e}",
                    exc_info=True
                )
                span.set_attribute("error", str(e))
                raise RuntimeError(f"Failed to retrieve explainability: {e}") from e

    async def get_recommendation_by_id(self, recommendation_id: UUID) -> dict[str, Any] | None:
        """
        Retrieve a single recommendation by ID.

        Args:
            recommendation_id: Target recommendation identifier

        Returns:
            Recommendation dictionary or None if not found
        """
        with tracer.start_as_current_span("recommendation_service.get_by_id") as span:
            span.set_attribute("recommendation_id", str(recommendation_id))

            # Mock mode for local development
            if os.getenv("ENV") == "local":
                logger.info(f"Mock mode: returning mock recommendation for {recommendation_id}")
                return {
                    "recommendation_id": str(recommendation_id),
                    "customer_id": "550e8400-e29b-41d4-a716-446655440001",
                    "recommendation_type": "Adoption",
                    "text_description": "Enable Advanced Reporting feature for better insights",
                    "confidence_score": 0.85,
                    "reasoning_chain": {
                        "retrieval": "Customer has high usage of Dashboard Analytics",
                        "sentiment": "Positive sentiment, no recent issues",
                        "reasoning": "Advanced Reporting complements current dashboard usage"
                    },
                    "generation_timestamp": datetime.utcnow().isoformat(),
                    "outcome_status": "Pending"
                }

            try:
                # Query Cosmos DB by document id
                # Note: We need to query across partitions since we don't have customer_id
                query = """
                    SELECT * FROM c 
                    WHERE c.recommendation_id = @recommendation_id
                """
                parameters = [
                    {"name": "@recommendation_id", "value": str(recommendation_id)}
                ]

                items = list(
                    self.recommendations_container.query_items(
                        query=query,
                        parameters=parameters,
                        enable_cross_partition_query=True
                    )
                )

                if not items:
                    logger.warning(f"Recommendation {recommendation_id} not found")
                    return None

                logger.info(f"Retrieved recommendation {recommendation_id}")
                return items[0]

            except Exception as e:
                logger.error(
                    f"Failed to retrieve recommendation {recommendation_id}: {e}",
                    exc_info=True
                )
                span.set_attribute("error", str(e))
                raise RuntimeError(f"Failed to retrieve recommendation: {e}") from e

    async def _graceful_degradation_result(
        self, customer_id: UUID, error_message: str
    ) -> dict[str, Any]:
        """
        Provide graceful degradation per FR-017.

        Returns empty recommendations with error metadata instead of failing completely.

        Args:
            customer_id: Target customer identifier
            error_message: Error message from failed generation

        Returns:
            Degraded result with empty recommendations
        """
        logger.warning(
            f"Graceful degradation: returning empty recommendations for customer {customer_id}"
        )

        return {
            "adoption_recommendations": [],
            "upsell_recommendations": [],
            "cached": False,
            "generation_time_ms": 0,
            "orchestration_metadata": {
                "customer_id": str(customer_id),
                "success": False,
                "error": error_message,
                "graceful_degradation": True,
            },
        }
