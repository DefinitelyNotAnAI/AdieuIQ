"""
Foundry IQ client for knowledge base retrieval and RAG patterns.

This client provides access to the Foundry IQ knowledge base for grounding
AI recommendations in documented best practices and product knowledge.

Constitutional Compliance:
- Uses Managed Identity (DefaultAzureCredential) for authentication
- Supports local development with mock data (ENV=local)
- Implements RAG (Retrieval-Augmented Generation) patterns
- No hardcoded credentials or API keys
"""

import logging
import os
from typing import Any
from uuid import UUID

from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential

from ..core.config import settings
from ..core.observability import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class KnowledgeArticle:
    """
    Knowledge article from Foundry IQ.

    Represents a knowledge base article that can be used to ground
    AI recommendations.
    """

    def __init__(
        self,
        article_id: str,
        title: str,
        content: str,
        relevance_score: float,
        category: str,
        tags: list[str] | None = None,
    ):
        """
        Initialize knowledge article.

        Args:
            article_id: Unique article identifier
            title: Article title
            content: Article content (excerpt or full text)
            relevance_score: Relevance to query (0.0 to 1.0)
            category: Article category (e.g., "Best Practices", "Troubleshooting")
            tags: Optional list of tags for categorization
        """
        self.article_id = article_id
        self.title = title
        self.content = content
        self.relevance_score = relevance_score
        self.category = category
        self.tags = tags or []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "article_id": self.article_id,
            "title": self.title,
            "content": self.content,
            "relevance_score": self.relevance_score,
            "category": self.category,
            "tags": self.tags,
        }


class FoundryIQClient:
    """
    Client for Foundry IQ knowledge base integration.

    Provides knowledge retrieval and search capabilities for RAG patterns.
    Supports mock mode for local development per quickstart.md.
    """

    def __init__(self, credential: TokenCredential | None = None):
        """
        Initialize Foundry IQ client.

        Args:
            credential: Azure credential for authentication. If None, uses DefaultAzureCredential.
        """
        self.use_mock = os.getenv("ENV") == "local"

        if self.use_mock:
            logger.info("FoundryIQClient initialized in MOCK mode (ENV=local)")
            self.credential = None
            self.endpoint = None
        else:
            self.credential = credential or DefaultAzureCredential()
            self.endpoint = settings.foundry_iq_endpoint
            logger.info(f"FoundryIQClient initialized with endpoint: {self.endpoint}")

    async def search_knowledge(
        self, query: str, top_k: int = 10, category_filter: str | None = None
    ) -> list[KnowledgeArticle]:
        """
        Search knowledge base using semantic search.

        Implements RAG pattern by retrieving relevant articles to ground
        AI recommendations (Constitutional requirement per quickstart.md).

        Args:
            query: Search query (natural language or keywords)
            top_k: Maximum number of results to return (default 10)
            category_filter: Optional category filter (e.g., "Best Practices")

        Returns:
            List of KnowledgeArticle objects ordered by relevance

        Raises:
            ValueError: If query is empty or top_k is not positive
            RuntimeError: If Foundry IQ query fails in production mode
        """
        if not query or not query.strip():
            raise ValueError("query cannot be empty")
        if top_k <= 0:
            raise ValueError("top_k must be positive")

        with tracer.start_as_current_span("foundry_iq.search_knowledge") as span:
            span.set_attribute("query", query)
            span.set_attribute("top_k", top_k)
            if category_filter:
                span.set_attribute("category_filter", category_filter)

            if self.use_mock:
                logger.debug(f"Returning mock knowledge articles for query: {query}")
                return self._get_mock_knowledge_articles(query, top_k)

            # Production: Query Foundry IQ knowledge base
            return await self._query_foundry_iq(query, top_k, category_filter)

    async def _query_foundry_iq(
        self, query: str, top_k: int, category_filter: str | None
    ) -> list[KnowledgeArticle]:
        """
        Query Foundry IQ knowledge base (production mode).

        Implementation placeholder - actual Foundry IQ API integration
        will be configured during Azure deployment.

        Args:
            query: Search query
            top_k: Maximum number of results
            category_filter: Optional category filter

        Returns:
            List of KnowledgeArticle objects from Foundry IQ

        Raises:
            RuntimeError: If Foundry IQ API call fails
        """
        # TODO: Implement actual Foundry IQ REST API call
        # Reference: https://learn.microsoft.com/azure/ai-foundry/foundry-iq
        #
        # Expected implementation:
        # 1. Acquire token using self.credential for Foundry IQ scope
        # 2. Submit semantic search query with embedding
        # 3. Parse response into KnowledgeArticle objects
        # 4. Apply category filter if specified
        # 5. Sort by relevance_score descending
        #
        # For now, raise NotImplementedError to fail fast during deployment
        raise NotImplementedError(
            "Foundry IQ production integration pending. "
            "Configure FOUNDRY_IQ_ENDPOINT in Key Vault and implement REST API client. "
            "See quickstart.md for RAG integration pattern."
        )

    def _get_mock_knowledge_articles(
        self, query: str, top_k: int
    ) -> list[KnowledgeArticle]:
        """
        Generate mock knowledge articles for local development.

        Creates realistic test data following the patterns in quickstart.md.

        Args:
            query: Search query
            top_k: Maximum number of results

        Returns:
            List of mock KnowledgeArticle objects
        """
        mock_articles = [
            KnowledgeArticle(
                article_id="kb_article_1234",
                title="Advanced Reporting Best Practices",
                content="Enable Advanced Reporting to gain deeper insights into supply chain bottlenecks. "
                "This feature provides drill-down capabilities, custom metric definitions, "
                "and automated anomaly detection. Customers who activate this feature "
                "report 40% faster decision-making cycles.",
                relevance_score=0.92,
                category="Best Practices",
                tags=["reporting", "analytics", "adoption"],
            ),
            KnowledgeArticle(
                article_id="kb_article_5678",
                title="API Integration Troubleshooting Guide",
                content="Common issues with API authentication: Ensure API keys are rotated every 90 days. "
                "Use OAuth2 for production integrations. Check rate limits (1000 req/min). "
                "For SSL certificate errors, verify certificate chain is complete.",
                relevance_score=0.87,
                category="Troubleshooting",
                tags=["api", "integration", "ssl", "authentication"],
            ),
            KnowledgeArticle(
                article_id="kb_article_9012",
                title="Custom Workflows Setup Guide",
                content="Custom Workflows allow automation of repetitive tasks. Start with simple triggers "
                "like 'New Record Created' and gradually add complex logic. "
                "Use the visual workflow editor for no-code setup. Test workflows in sandbox first.",
                relevance_score=0.79,
                category="Setup Guide",
                tags=["workflows", "automation", "configuration"],
            ),
            KnowledgeArticle(
                article_id="kb_article_3456",
                title="Upsell Opportunity: Enterprise Tier Features",
                content="Enterprise tier unlocks advanced security (SSO, MFA), dedicated support (SLA <4h), "
                "and unlimited API calls. Best suited for customers with >500 users or complex integrations. "
                "Typical ROI is 6 months for manufacturing customers.",
                relevance_score=0.85,
                category="Upsell Guide",
                tags=["enterprise", "upsell", "security", "support"],
            ),
            KnowledgeArticle(
                article_id="kb_article_7890",
                title="Data Export Feature Overview",
                content="Data Export supports CSV, Excel, JSON formats. Schedule automated exports daily/weekly. "
                "For large datasets (>100K rows), use incremental export mode. "
                "Exports are retained for 30 days in OneLake.",
                relevance_score=0.73,
                category="Feature Overview",
                tags=["export", "data", "onelake"],
            ),
        ]

        # Filter by query relevance (simple keyword matching for mock)
        query_lower = query.lower()
        filtered = [
            article
            for article in mock_articles
            if any(
                term in article.title.lower()
                or term in article.content.lower()
                or term in article.tags
                for term in query_lower.split()
            )
        ]

        # If no matches, return all articles
        if not filtered:
            filtered = mock_articles

        # Sort by relevance score descending
        filtered.sort(key=lambda x: x.relevance_score, reverse=True)

        # Return top_k results
        results = filtered[:top_k]
        logger.debug(f"Returning {len(results)} mock knowledge articles for query: {query}")
        return results

    async def get_article_by_id(self, article_id: str) -> KnowledgeArticle | None:
        """
        Retrieve a specific knowledge article by ID.

        Args:
            article_id: Unique article identifier

        Returns:
            KnowledgeArticle if found, None otherwise

        Raises:
            ValueError: If article_id is empty
        """
        if not article_id or not article_id.strip():
            raise ValueError("article_id cannot be empty")

        with tracer.start_as_current_span("foundry_iq.get_article_by_id") as span:
            span.set_attribute("article_id", article_id)

            if self.use_mock:
                # Return first mock article for simplicity
                articles = self._get_mock_knowledge_articles("", 5)
                for article in articles:
                    if article.article_id == article_id:
                        return article
                return None

            # Production: Query Foundry IQ by article ID
            raise NotImplementedError(
                "Foundry IQ article retrieval by ID pending production integration"
            )

    async def get_recommended_articles(
        self, customer_id: UUID, usage_patterns: list[str]
    ) -> list[KnowledgeArticle]:
        """
        Get recommended knowledge articles based on customer usage patterns.

        Uses customer usage history to recommend relevant knowledge articles
        for proactive guidance.

        Args:
            customer_id: Target customer identifier
            usage_patterns: List of feature names or usage categories

        Returns:
            List of recommended KnowledgeArticle objects

        Raises:
            ValueError: If usage_patterns is empty
        """
        if not usage_patterns:
            raise ValueError("usage_patterns cannot be empty")

        with tracer.start_as_current_span(
            "foundry_iq.get_recommended_articles"
        ) as span:
            span.set_attribute("customer_id", str(customer_id))
            span.set_attribute("pattern_count", len(usage_patterns))

            # Build query from usage patterns
            query = " ".join(usage_patterns)
            return await self.search_knowledge(query, top_k=5)
