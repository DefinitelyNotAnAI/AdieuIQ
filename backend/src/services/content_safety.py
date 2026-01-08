"""
Content Safety service for validating AI-generated text.

This service integrates with Azure AI Content Safety to filter harmful content
from all AI-generated recommendations before they reach support agents.

Constitutional Compliance (NON-NEGOTIABLE):
- Constitutional Principle III: "Apply Azure AI Content Safety filters to ALL AI-generated content"
- FR-019: All recommendation text must pass Content Safety validation
- Uses Managed Identity (DefaultAzureCredential) for authentication
- No hardcoded credentials or API keys
"""

import logging
import os
from typing import Any

from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import AnalyzeTextOptions, TextCategory
from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential

from ..core.config import settings
from ..core.observability import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class ContentSafetyResult:
    """
    Result of content safety analysis.

    Attributes:
        is_safe: Whether content passed all safety checks
        severity_scores: Dictionary of category -> severity score (0-7)
        blocked_categories: List of categories that exceeded threshold
        recommendation: Action to take ("Allow", "Block", "Review")
    """

    def __init__(
        self,
        is_safe: bool,
        severity_scores: dict[str, int],
        blocked_categories: list[str],
        recommendation: str = "Allow",
    ):
        self.is_safe = is_safe
        self.severity_scores = severity_scores
        self.blocked_categories = blocked_categories
        self.recommendation = recommendation

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "is_safe": self.is_safe,
            "severity_scores": self.severity_scores,
            "blocked_categories": self.blocked_categories,
            "recommendation": self.recommendation,
        }


class ContentSafetyService:
    """
    Service for validating AI-generated content using Azure AI Content Safety.

    Constitutional requirement: ALL AI-generated text must pass through this service
    before being shown to support agents or customers.
    """

    # Severity thresholds (0-7 scale from Azure AI Content Safety)
    # Values above threshold will block content
    SEVERITY_THRESHOLDS = {
        TextCategory.HATE: 2,  # Block moderate hate speech and above
        TextCategory.SELF_HARM: 2,  # Block moderate self-harm content and above
        TextCategory.SEXUAL: 4,  # Block high sexual content (more lenient for business context)
        TextCategory.VIOLENCE: 2,  # Block moderate violence and above
    }

    def __init__(self, credential: TokenCredential | None = None):
        """
        Initialize Content Safety service.

        Args:
            credential: Azure credential for authentication. If None, uses DefaultAzureCredential.
        """
        self.use_mock = os.getenv("ENV") == "local"

        if self.use_mock:
            logger.info("ContentSafetyService initialized in MOCK mode (ENV=local)")
            self.client = None
        else:
            credential = credential or DefaultAzureCredential()
            self.endpoint = settings.azure_openai_endpoint  # Content Safety often shares OpenAI endpoint
            self.client = ContentSafetyClient(
                endpoint=self.endpoint, credential=credential
            )
            logger.info(
                f"ContentSafetyService initialized with endpoint: {self.endpoint}"
            )

    async def validate_recommendation_text(self, text: str) -> ContentSafetyResult:
        """
        Validate recommendation text for harmful content.

        Constitutional requirement (FR-019): ALL recommendation text must pass
        Content Safety validation before being shown to users.

        Args:
            text: Recommendation text to validate

        Returns:
            ContentSafetyResult with validation outcome

        Raises:
            ValueError: If text is empty
            RuntimeError: If Content Safety API call fails in production mode
        """
        if not text or not text.strip():
            raise ValueError("text cannot be empty")

        with tracer.start_as_current_span("content_safety.validate_text") as span:
            span.set_attribute("text_length", len(text))

            if self.use_mock:
                logger.debug("Using mock Content Safety validation (always passes)")
                return self._get_mock_validation_result(text)

            # Production: Call Azure AI Content Safety
            return await self._analyze_text_production(text)

    async def _analyze_text_production(self, text: str) -> ContentSafetyResult:
        """
        Analyze text using Azure AI Content Safety (production mode).

        Args:
            text: Text to analyze

        Returns:
            ContentSafetyResult with severity scores and recommendation

        Raises:
            RuntimeError: If Content Safety API call fails
        """
        try:
            # Analyze text for all categories
            request = AnalyzeTextOptions(text=text)
            response = self.client.analyze_text(request)

            # Extract severity scores
            severity_scores = {}
            blocked_categories = []

            for category_result in response.categories_analysis:
                category = category_result.category
                severity = category_result.severity

                severity_scores[category] = severity

                # Check if severity exceeds threshold
                threshold = self.SEVERITY_THRESHOLDS.get(category, 6)
                if severity > threshold:
                    blocked_categories.append(category)
                    logger.warning(
                        f"Content Safety BLOCKED: category={category}, "
                        f"severity={severity}, threshold={threshold}"
                    )

            # Determine if content is safe
            is_safe = len(blocked_categories) == 0

            result = ContentSafetyResult(
                is_safe=is_safe,
                severity_scores=severity_scores,
                blocked_categories=blocked_categories,
                recommendation="Allow" if is_safe else "Block",
            )

            logger.info(f"Content Safety validation: {result.to_dict()}")
            return result

        except Exception as e:
            logger.error(f"Content Safety API call failed: {e}", exc_info=True)
            # Fail-safe: Block content if validation fails
            return ContentSafetyResult(
                is_safe=False,
                severity_scores={},
                blocked_categories=["API_ERROR"],
                recommendation="Block",
            )

    def _get_mock_validation_result(self, text: str) -> ContentSafetyResult:
        """
        Generate mock validation result for local development.

        Mock always passes for development convenience, but logs a warning
        to remind developers that production will enforce Content Safety.

        Args:
            text: Text being validated

        Returns:
            Mock ContentSafetyResult (always passes)
        """
        logger.warning(
            "MOCK MODE: Content Safety validation bypassed. "
            "Production will enforce Content Safety checks per FR-019."
        )

        # Simulate low severity scores (safe content)
        mock_scores = {
            TextCategory.HATE: 0,
            TextCategory.SELF_HARM: 0,
            TextCategory.SEXUAL: 0,
            TextCategory.VIOLENCE: 0,
        }

        return ContentSafetyResult(
            is_safe=True,
            severity_scores=mock_scores,
            blocked_categories=[],
            recommendation="Allow",
        )

    async def validate_batch(
        self, texts: list[str]
    ) -> dict[str, ContentSafetyResult]:
        """
        Validate multiple texts in batch.

        Useful for validating all recommendations from a single generation cycle.

        Args:
            texts: List of recommendation texts to validate

        Returns:
            Dictionary mapping text to ContentSafetyResult

        Raises:
            ValueError: If texts list is empty
        """
        if not texts:
            raise ValueError("texts list cannot be empty")

        with tracer.start_as_current_span("content_safety.validate_batch") as span:
            span.set_attribute("batch_size", len(texts))

            results = {}
            for i, text in enumerate(texts):
                with tracer.start_as_current_span(f"validate_item_{i}"):
                    result = await self.validate_recommendation_text(text)
                    results[text] = result

            # Log batch summary
            passed_count = sum(1 for r in results.values() if r.is_safe)
            blocked_count = len(results) - passed_count
            logger.info(
                f"Content Safety batch validation: {passed_count} passed, {blocked_count} blocked"
            )

            return results

    def get_blocked_recommendations_summary(
        self, results: dict[str, ContentSafetyResult]
    ) -> dict[str, Any]:
        """
        Generate summary of blocked recommendations for logging/analytics.

        Args:
            results: Dictionary of validation results from validate_batch

        Returns:
            Summary dictionary with blocked count and categories
        """
        blocked = [text for text, result in results.items() if not result.is_safe]
        blocked_categories = []

        for result in results.values():
            if not result.is_safe:
                blocked_categories.extend(result.blocked_categories)

        # Count category occurrences
        category_counts = {}
        for category in blocked_categories:
            category_counts[category] = category_counts.get(category, 0) + 1

        return {
            "total_validated": len(results),
            "blocked_count": len(blocked),
            "passed_count": len(results) - len(blocked),
            "blocked_category_counts": category_counts,
            "blocked_texts": blocked[:3],  # First 3 blocked texts for debugging
        }
