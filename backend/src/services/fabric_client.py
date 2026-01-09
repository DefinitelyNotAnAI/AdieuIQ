"""
Fabric IQ client for querying usage trends and semantic intelligence.

This client provides access to customer usage data via the Fabric IQ semantic layer.
It abstracts the OneLake data lake and provides aggregated views of feature usage.

Constitutional Compliance:
- Uses Managed Identity (DefaultAzureCredential) for authentication
- Supports local development with mock data (ENV=local)
- No hardcoded credentials or API keys
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import redis.asyncio as redis
from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential

from ..core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
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
        Initialize Fabric IQ client with Redis caching and circuit breaker (T065, T066).

        Args:
            credential: Azure credential for authentication. If None, uses DefaultAzureCredential.
        """
        self.use_mock = os.getenv("ENV") == "local"

        # Initialize circuit breaker (T066 - graceful degradation per FR-017)
        self.circuit_breaker = CircuitBreaker(
            name="Fabric IQ",
            failure_threshold=5,  # Open after 5 failures
            timeout=60.0,  # Wait 60s before retry
            half_open_max_calls=1  # Test with 1 call in HALF_OPEN state
        )

        # Initialize Redis client (T065 - caching for usage trends)
        redis_hostname = os.getenv("REDIS_HOSTNAME")
        redis_port = int(os.getenv("REDIS_PORT", "6380"))
        redis_password = os.getenv("REDIS_ACCESS_KEY")
        
        if self.use_mock or not redis_hostname:
            logger.info("Redis caching disabled (local mode or REDIS_HOSTNAME not set)")
            self.redis_client = None
        else:
            try:
                self.redis_client = redis.Redis(
                    host=redis_hostname,
                    port=redis_port,
                    password=redis_password,
                    ssl=True,
                    decode_responses=True
                )
                logger.info(f"FabricIQClient: Redis initialized for caching")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis client: {e}. Caching disabled.")
                self.redis_client = None

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
        Get customer usage trends with Redis caching (T065).

        Cache Strategy (per quickstart.md optimization tip):
        - Cache key: usage_trends:{customer_id}:{days}
        - TTL: 1 hour (3600 seconds)
        - Usage data changes slowly, caching reduces Fabric IQ load

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

            # Try Redis cache first (T065)
            cache_key = f"usage_trends:{customer_id}:{days}"
            if self.redis_client:
                try:
                    cached_data = await self.redis_client.get(cache_key)
                    if cached_data:
                        logger.info(f"Cache HIT for usage trends {customer_id} (days={days})")
                        span.set_attribute("cache_hit", True)
                        # Deserialize UsageData objects from JSON
                        usage_list = json.loads(cached_data)
                        return [UsageData(**item) for item in usage_list]
                    else:
                        logger.debug(f"Cache MISS for usage trends {customer_id}")
                        span.set_attribute("cache_hit", False)
                except Exception as e:
                    logger.warning(f"Redis cache read failed: {e}. Proceeding without cache.")
                    span.set_attribute("cache_error", str(e))

            # Production: Query Fabric IQ semantic layer with circuit breaker (T066)
            try:
                usage_data = await self.circuit_breaker.call(
                    self._query_fabric_iq, customer_id, days
                )
            except CircuitBreakerOpenError as e:
                logger.warning(f"Circuit breaker open for Fabric IQ: {e}")
                span.set_attribute("circuit_breaker_open", True)
                # Graceful degradation: Return empty usage data
                return []

            # Store in Redis cache with 1-hour TTL (T065)
            if self.redis_client and usage_data:
                try:
                    # Serialize UsageData objects to JSON
                    usage_dicts = [item.model_dump() for item in usage_data]
                    await self.redis_client.setex(
                        cache_key,
                        3600,  # 1 hour TTL per quickstart.md
                        json.dumps(usage_dicts, default=str)
                    )
                    logger.debug(f"Cached usage trends {customer_id} for 1 hour")
                except Exception as e:
                    logger.warning(f"Redis cache write failed: {e}")
                    span.set_attribute("cache_write_error", str(e))

            return usage_data

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
