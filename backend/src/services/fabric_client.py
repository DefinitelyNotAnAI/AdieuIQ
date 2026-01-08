"""
Fabric IQ client for querying usage trends and semantic intelligence.

This client provides access to customer usage data via the Fabric IQ semantic layer.
It abstracts the OneLake data lake and provides aggregated views of feature usage.

Constitutional Compliance:
- Uses Managed Identity (DefaultAzureCredential) for authentication
- Supports local development with mock data (ENV=local)
- No hardcoded credentials or API keys
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential

from ..core.config import settings
from ..core.observability import get_tracer
from ..models.usage_data import IntensityScore, UsageData

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class FabricIQClient:
    """
    Client for Fabric IQ semantic layer integration.

    Queries usage trends from OneLake via Fabric IQ REST API.
    Supports mock mode for local development per quickstart.md.
    """

    def __init__(self, credential: TokenCredential | None = None):
        """
        Initialize Fabric IQ client.

        Args:
            credential: Azure credential for authentication. If None, uses DefaultAzureCredential.
        """
        self.use_mock = os.getenv("ENV") == "local"

        if self.use_mock:
            logger.info("FabricIQClient initialized in MOCK mode (ENV=local)")
            self.credential = None
            self.endpoint = None
        else:
            self.credential = credential or DefaultAzureCredential()
            self.endpoint = settings.fabric_iq_endpoint
            logger.info(f"FabricIQClient initialized with endpoint: {self.endpoint}")

    async def get_usage_trends(
        self, customer_id: UUID, days: int = 90
    ) -> list[UsageData]:
        """
        Get customer usage trends for the past N days.

        Args:
            customer_id: Target customer identifier
            days: Number of days to look back (default 90 per FR-002)

        Returns:
            List of UsageData records with feature usage and intensity scores

        Raises:
            ValueError: If days is not positive
            RuntimeError: If Fabric IQ query fails in production mode
        """
        if days <= 0:
            raise ValueError("days must be positive")

        with tracer.start_as_current_span("fabric_iq.get_usage_trends") as span:
            span.set_attribute("customer_id", str(customer_id))
            span.set_attribute("days", days)

            if self.use_mock:
                logger.debug(f"Returning mock usage data for customer {customer_id}")
                return self._get_mock_usage_data(customer_id, days)

            # Production: Query Fabric IQ semantic layer
            return await self._query_fabric_iq(customer_id, days)

    async def _query_fabric_iq(
        self, customer_id: UUID, days: int
    ) -> list[UsageData]:
        """
        Query Fabric IQ semantic layer (production mode).

        Implementation placeholder - actual Fabric IQ API integration
        will be configured during Azure deployment.

        Args:
            customer_id: Target customer identifier
            days: Number of days to look back

        Returns:
            List of UsageData records from Fabric IQ

        Raises:
            RuntimeError: If Fabric IQ API call fails
        """
        # TODO: Implement actual Fabric IQ REST API call
        # Reference: https://learn.microsoft.com/fabric/
        #
        # Expected implementation:
        # 1. Acquire token using self.credential for Fabric IQ scope
        # 2. Query semantic layer endpoint with customer_id filter
        # 3. Parse response into UsageData models
        # 4. Apply time window aggregation (daily/weekly)
        #
        # For now, raise NotImplementedError to fail fast during deployment
        raise NotImplementedError(
            "Fabric IQ production integration pending. "
            "Configure FABRIC_IQ_ENDPOINT in Key Vault and implement REST API client. "
            "See quickstart.md for integration pattern."
        )

    def _get_mock_usage_data(
        self, customer_id: UUID, days: int
    ) -> list[UsageData]:
        """
        Generate mock usage data for local development.

        Creates realistic test data following the patterns in quickstart.md.

        Args:
            customer_id: Target customer identifier
            days: Number of days to look back

        Returns:
            List of mock UsageData records
        """
        import uuid

        now = datetime.utcnow()
        mock_features = [
            ("Dashboard Analytics", 142, IntensityScore.HIGH),
            ("API Integration", 87, IntensityScore.MEDIUM),
            ("Data Export", 12, IntensityScore.LOW),
            ("Advanced Reporting", 0, IntensityScore.NONE),
            ("Custom Workflows", 34, IntensityScore.MEDIUM),
        ]

        usage_records = []
        for feature_name, usage_count, intensity in mock_features:
            usage_records.append(
                UsageData(
                    usage_id=uuid.uuid4(),
                    customer_id=customer_id,
                    feature_name=feature_name,
                    usage_count=usage_count,
                    last_used_timestamp=now - timedelta(days=2),
                    intensity_score=intensity,
                    time_window="weekly",
                    recorded_at=now,
                )
            )

        logger.debug(
            f"Generated {len(usage_records)} mock usage records for customer {customer_id}"
        )
        return usage_records

    async def get_semantic_context(
        self, customer_id: UUID, feature_name: str
    ) -> dict[str, Any]:
        """
        Get semantic context for a specific feature.

        Retrieves aggregated insights about feature usage patterns,
        correlations, and adoption trends from Fabric IQ.

        Args:
            customer_id: Target customer identifier
            feature_name: Name of the feature to analyze

        Returns:
            Dictionary with semantic context (adoption_rate, peer_comparison, trend)

        Raises:
            ValueError: If feature_name is empty
        """
        if not feature_name or not feature_name.strip():
            raise ValueError("feature_name cannot be empty")

        with tracer.start_as_current_span("fabric_iq.get_semantic_context") as span:
            span.set_attribute("customer_id", str(customer_id))
            span.set_attribute("feature_name", feature_name)

            if self.use_mock:
                return self._get_mock_semantic_context(feature_name)

            # Production: Query Fabric IQ for semantic insights
            raise NotImplementedError(
                "Fabric IQ semantic context query pending production integration"
            )

    def _get_mock_semantic_context(self, feature_name: str) -> dict[str, Any]:
        """
        Generate mock semantic context for local development.

        Args:
            feature_name: Name of the feature to analyze

        Returns:
            Mock semantic context dictionary
        """
        return {
            "feature_name": feature_name,
            "adoption_rate": 0.42,  # 42% of customers use this feature
            "peer_comparison": "above_average",  # This customer's usage vs peers
            "trend": "increasing",  # Usage trend over past 30 days
            "recommended_next_steps": [
                "Enable advanced analytics module",
                "Configure automated alerts",
            ],
        }
