"""
Validation Agent for multi-agent orchestration.

This agent validates recommendation candidates to ensure quality,
safety, and constitutional compliance before delivery.

Constitutional Compliance:
- Part of Azure AI Foundry SDK orchestration (Constitutional Principle V)
- Enforces Content Safety filtering per FR-019 (Constitutional Principle III - NON-NEGOTIABLE)
- Prevents duplicate recommendations per FR-014
- Runs sequentially after Reasoning Agent (T030)
"""

import asyncio
import logging
from typing import Any
from uuid import UUID

from ...core.observability import get_tracer
from ...services.content_safety import ContentSafetyService

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class ValidationAgent:
    """
    Validation Agent for quality assurance and safety checks.

    Validates recommendation candidates to ensure:
    1. No duplicate recommendations (FR-014)
    2. Content Safety compliance (FR-019 - Constitutional requirement)
    3. Constitutional compliance checks
    4. Minimum confidence thresholds

    This agent runs sequentially after Reasoning Agent completes.
    """

    def __init__(self, content_safety_service: ContentSafetyService | None = None):
        """
        Initialize Validation Agent.

        Args:
            content_safety_service: Content Safety service for text validation (optional, creates new if None)
        """
        self.content_safety_service = content_safety_service or ContentSafetyService()
        logger.info("ValidationAgent initialized")

    async def run(
        self,
        customer_id: UUID,
        reasoning_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute validation agent workflow.

        Validates all recommendation candidates from Reasoning Agent:
        - Check for duplicates against historical recommendations (FR-014)
        - Apply Content Safety filters to all text (FR-019)
        - Enforce minimum confidence thresholds
        - Log validation decisions for audit trail

        Args:
            customer_id: Target customer identifier
            reasoning_result: Output from Reasoning Agent (T030)

        Returns:
            Dictionary containing:
            - validated_recommendations: List of recommendations that passed all checks
            - blocked_recommendations: List of recommendations that were filtered
            - validation_summary: Summary of validation results
            - execution_time_ms: Agent execution time

        Raises:
            ValueError: If customer_id is invalid or reasoning_result is malformed
        """
        with tracer.start_as_current_span("validation_agent.run") as span:
            span.set_attribute("customer_id", str(customer_id))

            start_time = asyncio.get_event_loop().time()

            try:
                # Phase 1: Extract candidates from reasoning result
                adoption_candidates = reasoning_result.get(
                    "adoption_recommendations", []
                )
                upsell_candidates = reasoning_result.get("upsell_recommendations", [])
                all_candidates = adoption_candidates + upsell_candidates

                span.set_attribute("candidate_count", len(all_candidates))

                if not all_candidates:
                    logger.warning(
                        f"No recommendation candidates to validate for customer {customer_id}"
                    )
                    return self._build_empty_result(start_time)

                # Phase 2: Check for duplicates (FR-014)
                candidates_after_dedup = await self._check_duplicates(
                    customer_id, all_candidates
                )

                # Phase 3: Apply Content Safety filters (FR-019)
                candidates_after_safety = await self._validate_content_safety(
                    candidates_after_dedup
                )

                # Phase 4: Enforce minimum confidence thresholds
                validated_recommendations = self._filter_low_confidence(
                    candidates_after_safety, min_confidence=0.5
                )

                # Calculate blocked recommendations
                blocked_recommendations = [
                    c
                    for c in all_candidates
                    if c not in validated_recommendations
                ]

                # Calculate execution time
                end_time = asyncio.get_event_loop().time()
                execution_time_ms = int((end_time - start_time) * 1000)

                result = {
                    "validated_recommendations": validated_recommendations,
                    "blocked_recommendations": [
                        {
                            "recommendation_id": r.get("recommendation_id"),
                            "text_description": r.get("text_description", "")[:100],
                            "block_reason": self._determine_block_reason(
                                r, all_candidates, candidates_after_dedup, candidates_after_safety
                            ),
                        }
                        for r in blocked_recommendations
                    ],
                    "validation_summary": {
                        "total_candidates": len(all_candidates),
                        "duplicate_filtered": len(all_candidates)
                        - len(candidates_after_dedup),
                        "content_safety_blocked": len(candidates_after_dedup)
                        - len(candidates_after_safety),
                        "low_confidence_filtered": len(candidates_after_safety)
                        - len(validated_recommendations),
                        "validated_count": len(validated_recommendations),
                    },
                    "execution_time_ms": execution_time_ms,
                }

                span.set_attribute("validated_count", len(validated_recommendations))
                span.set_attribute("blocked_count", len(blocked_recommendations))
                span.set_attribute("execution_time_ms", execution_time_ms)

                logger.info(
                    f"ValidationAgent completed: customer_id={customer_id}, "
                    f"validated={len(validated_recommendations)}, blocked={len(blocked_recommendations)}, "
                    f"execution_time={execution_time_ms}ms"
                )

                return result

            except Exception as e:
                logger.error(f"ValidationAgent failed: {e}", exc_info=True)
                span.set_attribute("error", str(e))
                raise

    async def _check_duplicates(
        self, customer_id: UUID, candidates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Check for duplicate recommendations per FR-014.

        Queries historical recommendations from Cosmos DB and filters out
        candidates that are too similar to previously generated recommendations.

        Args:
            customer_id: Target customer identifier
            candidates: List of recommendation candidates

        Returns:
            Filtered list with duplicates removed
        """
        with tracer.start_as_current_span("validation_agent.check_duplicates"):
            # TODO: Implement actual Cosmos DB query for historical recommendations
            # Reference: azure.cosmos.CosmosClient
            #
            # Expected implementation:
            # 1. Query recommendations container with customer_id partition key
            # 2. Filter by outcome_status != 'Excluded'
            # 3. Compare candidate text with historical recommendations (similarity threshold)
            # 4. Remove candidates that are >80% similar to recent recommendations
            #
            # For now, assume no duplicates in local development
            import os

            if os.getenv("ENV") == "local":
                logger.debug(
                    f"Duplicate check: No historical recommendations in mock mode"
                )
                return candidates
            else:
                raise NotImplementedError(
                    "Cosmos DB duplicate check pending production integration. "
                    "Implement similarity comparison with historical recommendations."
                )

    async def _validate_content_safety(
        self, candidates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Apply Content Safety filters to all recommendation text per FR-019.

        Constitutional requirement (NON-NEGOTIABLE): ALL AI-generated text
        must pass Content Safety validation.

        Args:
            candidates: List of recommendation candidates

        Returns:
            Filtered list with unsafe content removed
        """
        with tracer.start_as_current_span("validation_agent.content_safety"):
            # Extract all text descriptions
            texts = [c.get("text_description", "") for c in candidates]

            # Batch validate with Content Safety service
            validation_results = await self.content_safety_service.validate_batch(
                texts
            )

            # Filter out candidates with unsafe content
            safe_candidates = []
            for candidate in candidates:
                text = candidate.get("text_description", "")
                result = validation_results.get(text)

                if result and result.is_safe:
                    safe_candidates.append(candidate)
                else:
                    blocked_categories = (
                        result.blocked_categories if result else ["UNKNOWN"]
                    )
                    logger.warning(
                        f"Content Safety BLOCKED recommendation: "
                        f"recommendation_id={candidate.get('recommendation_id')}, "
                        f"categories={blocked_categories}"
                    )
                    # Add block reason to candidate for audit trail
                    candidate["_content_safety_blocked"] = True
                    candidate["_blocked_categories"] = blocked_categories

            logger.info(
                f"Content Safety validation: {len(safe_candidates)}/{len(candidates)} passed"
            )

            return safe_candidates

    def _filter_low_confidence(
        self, candidates: list[dict[str, Any]], min_confidence: float
    ) -> list[dict[str, Any]]:
        """
        Filter out recommendations below minimum confidence threshold.

        Args:
            candidates: List of recommendation candidates
            min_confidence: Minimum confidence score (0.0 to 1.0)

        Returns:
            Filtered list with low-confidence recommendations removed
        """
        filtered = [
            c
            for c in candidates
            if c.get("confidence_score", 0.0) >= min_confidence
        ]

        if len(filtered) < len(candidates):
            logger.info(
                f"Filtered {len(candidates) - len(filtered)} low-confidence recommendations "
                f"(threshold={min_confidence})"
            )

        return filtered

    def _determine_block_reason(
        self,
        recommendation: dict[str, Any],
        all_candidates: list[dict[str, Any]],
        after_dedup: list[dict[str, Any]],
        after_safety: list[dict[str, Any]],
    ) -> str:
        """
        Determine why a recommendation was blocked.

        Args:
            recommendation: Blocked recommendation
            all_candidates: Original candidate list
            after_dedup: List after duplicate check
            after_safety: List after content safety check

        Returns:
            Block reason string
        """
        rec_id = recommendation.get("recommendation_id")

        # Check if blocked by duplicate check
        if recommendation in all_candidates and recommendation not in after_dedup:
            return "duplicate"

        # Check if blocked by content safety
        if recommendation in after_dedup and recommendation not in after_safety:
            categories = recommendation.get("_blocked_categories", [])
            return f"content_safety: {', '.join(categories)}"

        # Check if blocked by low confidence
        if recommendation in after_safety:
            confidence = recommendation.get("confidence_score", 0.0)
            return f"low_confidence: {confidence:.2f}"

        return "unknown"

    def _build_empty_result(self, start_time: float) -> dict[str, Any]:
        """
        Build empty result when no candidates are provided.

        Args:
            start_time: Agent start time

        Returns:
            Empty validation result dictionary
        """
        end_time = asyncio.get_event_loop().time()
        execution_time_ms = int((end_time - start_time) * 1000)

        return {
            "validated_recommendations": [],
            "blocked_recommendations": [],
            "validation_summary": {
                "total_candidates": 0,
                "duplicate_filtered": 0,
                "content_safety_blocked": 0,
                "low_confidence_filtered": 0,
                "validated_count": 0,
            },
            "execution_time_ms": execution_time_ms,
        }
