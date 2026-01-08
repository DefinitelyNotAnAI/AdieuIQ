"""
Retrieval Agent for multi-agent orchestration.

This agent queries Fabric IQ and Foundry IQ in parallel to retrieve:
- Customer usage trends and intensity patterns
- Relevant knowledge base articles for grounding recommendations

Constitutional Compliance:
- Part of Azure AI Foundry SDK orchestration (Constitutional Principle V)
- Implements RAG (Retrieval-Augmented Generation) pattern
- Queries run in parallel to optimize latency (FR-005: <2s p95)
"""

import asyncio
import logging
from typing import Any
from uuid import UUID

from ...core.observability import get_tracer
from ...models.usage_data import UsageData
from ...services.fabric_client import FabricIQClient
from ...services.foundry_client import FoundryIQClient, KnowledgeArticle

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class RetrievalAgent:
    """
    Retrieval Agent for RAG pattern implementation.

    Queries Fabric IQ (usage data) and Foundry IQ (knowledge base) in parallel
    to ground recommendations in actual customer behavior and documented best practices.

    This agent is the first phase of the multi-agent orchestration workflow.
    """

    def __init__(
        self,
        fabric_client: FabricIQClient | None = None,
        foundry_client: FoundryIQClient | None = None,
    ):
        """
        Initialize Retrieval Agent.

        Args:
            fabric_client: Client for Fabric IQ integration (optional, creates new if None)
            foundry_client: Client for Foundry IQ integration (optional, creates new if None)
        """
        self.fabric_client = fabric_client or FabricIQClient()
        self.foundry_client = foundry_client or FoundryIQClient()
        logger.info("RetrievalAgent initialized")

    async def run(self, customer_id: UUID, days: int = 90) -> dict[str, Any]:
        """
        Execute retrieval agent workflow.

        Queries Fabric IQ and Foundry IQ in parallel to retrieve usage trends
        and relevant knowledge articles. This grounds recommendations in actual
        data (Constitutional requirement: RAG pattern).

        Args:
            customer_id: Target customer identifier
            days: Number of days to look back for usage data (default 90 per FR-002)

        Returns:
            Dictionary containing:
            - usage_data: List of UsageData objects
            - knowledge_articles: List of KnowledgeArticle objects
            - confidence: Confidence score (0.0 to 1.0)
            - execution_time_ms: Agent execution time

        Raises:
            ValueError: If customer_id is invalid or days is not positive
        """
        with tracer.start_as_current_span("retrieval_agent.run") as span:
            span.set_attribute("customer_id", str(customer_id))
            span.set_attribute("days", days)

            start_time = asyncio.get_event_loop().time()

            try:
                # Phase 1: Parallel retrieval from Fabric IQ + Foundry IQ
                # Constitutional requirement: Optimize latency with parallel execution
                with tracer.start_as_current_span("parallel_retrieval"):
                    usage_task = self.fabric_client.get_usage_trends(
                        customer_id=customer_id, days=days
                    )
                    
                    # Build knowledge search query based on anticipated usage patterns
                    # This will be refined with actual usage data in reasoning agent
                    knowledge_task = self.foundry_client.search_knowledge(
                        query="feature adoption best practices troubleshooting",
                        top_k=10,
                    )

                    usage_data, knowledge_articles = await asyncio.gather(
                        usage_task, knowledge_task
                    )

                # Phase 2: Calculate confidence based on data quality
                confidence = self._calculate_confidence(usage_data, knowledge_articles)

                # Phase 3: Build search query for refined knowledge retrieval
                if usage_data:
                    refined_query = self._build_search_query(usage_data)
                    with tracer.start_as_current_span("refined_knowledge_search"):
                        refined_knowledge = await self.foundry_client.search_knowledge(
                            query=refined_query, top_k=5
                        )
                    # Combine with initial results, deduplicate
                    all_articles = self._deduplicate_articles(
                        knowledge_articles + refined_knowledge
                    )
                else:
                    all_articles = knowledge_articles

                # Calculate execution time
                end_time = asyncio.get_event_loop().time()
                execution_time_ms = int((end_time - start_time) * 1000)

                result = {
                    "usage_data": [self._usage_data_to_dict(u) for u in usage_data],
                    "knowledge_articles": [a.to_dict() for a in all_articles],
                    "confidence": confidence,
                    "execution_time_ms": execution_time_ms,
                }

                span.set_attribute("confidence", confidence)
                span.set_attribute("execution_time_ms", execution_time_ms)
                span.set_attribute("usage_data_count", len(usage_data))
                span.set_attribute("knowledge_article_count", len(all_articles))

                logger.info(
                    f"RetrievalAgent completed: customer_id={customer_id}, "
                    f"confidence={confidence:.2f}, execution_time={execution_time_ms}ms"
                )

                return result

            except Exception as e:
                logger.error(f"RetrievalAgent failed: {e}", exc_info=True)
                span.set_attribute("error", str(e))
                raise

    def _build_search_query(self, usage_data: list[UsageData]) -> str:
        """
        Build refined search query based on usage patterns.

        Args:
            usage_data: List of usage data records

        Returns:
            Search query string optimized for knowledge retrieval
        """
        # Extract low-adoption features (potential adoption recommendations)
        low_adoption_features = [
            u.feature_name
            for u in usage_data
            if u.intensity_score.value in ["None", "Low"]
        ]

        # Extract high-adoption features (potential upsell opportunities)
        high_adoption_features = [
            u.feature_name
            for u in usage_data
            if u.intensity_score.value == "High"
        ]

        # Build query focusing on adoption and upsell opportunities
        query_parts = []
        if low_adoption_features:
            query_parts.append(
                f"adoption best practices for {' '.join(low_adoption_features[:3])}"
            )
        if high_adoption_features:
            query_parts.append(
                f"upsell opportunities for customers using {' '.join(high_adoption_features[:2])}"
            )

        if not query_parts:
            # Fallback: general query
            query_parts.append("product adoption recommendations")

        return " ".join(query_parts)

    def _calculate_confidence(
        self, usage_data: list[UsageData], knowledge_articles: list[KnowledgeArticle]
    ) -> float:
        """
        Calculate confidence score based on data quality.

        Confidence is higher when:
        - More usage data is available
        - Knowledge articles have high relevance scores
        - Usage patterns are clear (not all zero usage)

        Args:
            usage_data: List of usage data records
            knowledge_articles: List of knowledge articles

        Returns:
            Confidence score (0.0 to 1.0)
        """
        if not usage_data and not knowledge_articles:
            return 0.0

        # Component 1: Usage data availability (0-0.4)
        usage_score = min(len(usage_data) / 10.0, 0.4)

        # Component 2: Knowledge article relevance (0-0.4)
        if knowledge_articles:
            avg_relevance = sum(a.relevance_score for a in knowledge_articles) / len(
                knowledge_articles
            )
            knowledge_score = avg_relevance * 0.4
        else:
            knowledge_score = 0.0

        # Component 3: Usage pattern clarity (0-0.2)
        # Higher if we have mix of high and low usage (clear opportunities)
        if usage_data:
            intensities = [u.intensity_score.value for u in usage_data]
            has_high = "High" in intensities
            has_low = "Low" in intensities or "None" in intensities
            pattern_score = 0.2 if (has_high and has_low) else 0.1
        else:
            pattern_score = 0.0

        confidence = usage_score + knowledge_score + pattern_score
        return min(confidence, 1.0)  # Cap at 1.0

    def _deduplicate_articles(
        self, articles: list[KnowledgeArticle]
    ) -> list[KnowledgeArticle]:
        """
        Remove duplicate articles by article_id.

        Args:
            articles: List of knowledge articles (may contain duplicates)

        Returns:
            Deduplicated list, sorted by relevance score descending
        """
        seen_ids = set()
        unique_articles = []

        for article in articles:
            if article.article_id not in seen_ids:
                seen_ids.add(article.article_id)
                unique_articles.append(article)

        # Sort by relevance descending
        unique_articles.sort(key=lambda x: x.relevance_score, reverse=True)
        return unique_articles

    def _usage_data_to_dict(self, usage_data: UsageData) -> dict[str, Any]:
        """
        Convert UsageData to dictionary for serialization.

        Args:
            usage_data: UsageData object

        Returns:
            Dictionary representation
        """
        return {
            "usage_id": str(usage_data.usage_id),
            "customer_id": str(usage_data.customer_id),
            "feature_name": usage_data.feature_name,
            "usage_count": usage_data.usage_count,
            "last_used_timestamp": usage_data.last_used_timestamp.isoformat(),
            "intensity_score": usage_data.intensity_score.value,
            "time_window": usage_data.time_window,
        }
