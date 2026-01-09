"""
Reasoning Agent for multi-agent orchestration.

This agent combines retrieval results and sentiment analysis to generate
candidate recommendations using business logic and AI reasoning.

Constitutional Compliance:
- Part of Azure AI Foundry SDK orchestration (Constitutional Principle V)
- Implements sentiment-aware filtering per FR-015
- Generates 2-5 adoption + 1-3 upsell recommendations per FR-003/FR-004
- Runs sequentially after Retrieval Agent (T028) and Sentiment Agent (T029)
"""

import asyncio
import logging
from typing import Any
from uuid import UUID
import uuid

from ...core.observability import get_tracer
from ...models.recommendation import RecommendationType

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class ReasoningAgent:
    """
    Reasoning Agent for generating candidate recommendations.

    Combines retrieval results (usage data + knowledge articles) with
    sentiment analysis to generate personalized recommendations.

    This agent runs sequentially after Retrieval Agent and Sentiment Agent
    complete their parallel execution.
    """

    def __init__(self):
        """Initialize Reasoning Agent."""
        logger.info("ReasoningAgent initialized")

    async def run(
        self,
        customer_id: UUID,
        retrieval_result: dict[str, Any],
        sentiment_result: dict[str, Any],
        past_recommendations: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Execute reasoning agent workflow.

        Combines retrieval and sentiment data to generate candidate recommendations
        using business rules and AI reasoning patterns.

        Per FR-014 (US3/T057), checks for previously declined recommendations to avoid
        duplicates or provides re-suggesting reasoning if appropriate.

        Args:
            customer_id: Target customer identifier
            retrieval_result: Output from Retrieval Agent (T028)
            sentiment_result: Output from Sentiment Agent (T029)
            past_recommendations: Historical recommendations from last 12 months (optional)

        Returns:
            Dictionary containing:
            - adoption_recommendations: List of adoption recommendation candidates (2-5 per FR-003)
            - upsell_recommendations: List of upsell recommendation candidates (1-3 per FR-004)
            - reasoning_metadata: Metadata about reasoning process
            - execution_time_ms: Agent execution time

        Raises:
            ValueError: If customer_id is invalid or input data is malformed
        """
        with tracer.start_as_current_span("reasoning_agent.run") as span:
            span.set_attribute("customer_id", str(customer_id))

            start_time = asyncio.get_event_loop().time()

            try:
                # Phase 1: Extract and validate inputs
                usage_data = retrieval_result.get("usage_data", [])
                knowledge_articles = retrieval_result.get("knowledge_articles", [])
                sentiment_score = sentiment_result.get("sentiment_score", 0.0)
                sentiment_factors = sentiment_result.get("sentiment_factors", [])
                past_recs = past_recommendations or []

                span.set_attribute("usage_data_count", len(usage_data))
                span.set_attribute("knowledge_article_count", len(knowledge_articles))
                span.set_attribute("sentiment_score", sentiment_score)
                span.set_attribute("past_recommendations_count", len(past_recs))

                # Phase 2: Generate adoption recommendations (FR-003: 2-5 recommendations)
                adoption_candidates = await self._generate_adoption_recommendations(
                    customer_id, usage_data, knowledge_articles, sentiment_score
                )

                # Phase 3: Generate upsell recommendations (FR-004: 1-3 recommendations)
                upsell_candidates = await self._generate_upsell_recommendations(
                    customer_id, usage_data, knowledge_articles, sentiment_score
                )

                # Phase 4: Check for duplicates/declined recommendations (FR-014 per US3/T057)
                adoption_candidates = self._filter_past_recommendations(
                    adoption_candidates, past_recs
                )
                upsell_candidates = self._filter_past_recommendations(
                    upsell_candidates, past_recs
                )

                # Phase 5: Apply sentiment-aware filtering (FR-015)
                filtered_adoption = self._apply_sentiment_filter(
                    adoption_candidates, sentiment_score, sentiment_factors
                )
                filtered_upsell = self._apply_sentiment_filter(
                    upsell_candidates, sentiment_score, sentiment_factors
                )

                # Phase 6: Enforce count constraints
                final_adoption = filtered_adoption[
                    :5
                ]  # Cap at 5 (FR-003 allows 2-5)
                final_upsell = filtered_upsell[:3]  # Cap at 3 (FR-004 allows 1-3)

                # Calculate execution time
                end_time = asyncio.get_event_loop().time()
                execution_time_ms = int((end_time - start_time) * 1000)

                result = {
                    "adoption_recommendations": final_adoption,
                    "upsell_recommendations": final_upsell,
                    "reasoning_metadata": {
                        "sentiment_score": sentiment_score,
                        "sentiment_factors": sentiment_factors,
                        "usage_patterns_analyzed": len(usage_data),
                        "knowledge_articles_used": len(knowledge_articles),
                        "past_recommendations_checked": len(past_recs),
                        "filtered_count": len(adoption_candidates)
                        + len(upsell_candidates)
                        - len(final_adoption)
                        - len(final_upsell),
                    },
                    "execution_time_ms": execution_time_ms,
                }

                span.set_attribute("adoption_count", len(final_adoption))
                span.set_attribute("upsell_count", len(final_upsell))
                span.set_attribute("execution_time_ms", execution_time_ms)

                logger.info(
                    f"ReasoningAgent completed: customer_id={customer_id}, "
                    f"adoption={len(final_adoption)}, upsell={len(final_upsell)}, "
                    f"execution_time={execution_time_ms}ms"
                )

                return result

            except Exception as e:
                logger.error(f"ReasoningAgent failed: {e}", exc_info=True)
                span.set_attribute("error", str(e))
                raise

    async def _generate_adoption_recommendations(
        self,
        customer_id: UUID,
        usage_data: list[dict[str, Any]],
        knowledge_articles: list[dict[str, Any]],
        sentiment_score: float,
    ) -> list[dict[str, Any]]:
        """
        Generate adoption recommendation candidates.

        Identifies underutilized features and matches with knowledge articles
        to create adoption recommendations.

        Args:
            customer_id: Target customer identifier
            usage_data: List of usage data dictionaries
            knowledge_articles: List of knowledge article dictionaries
            sentiment_score: Customer sentiment score

        Returns:
            List of adoption recommendation candidates
        """
        recommendations = []

        # Identify low-adoption features (None or Low intensity)
        low_adoption_features = [
            u
            for u in usage_data
            if u.get("intensity_score") in ["None", "Low"]
        ]

        # Match each low-adoption feature with relevant knowledge articles
        for feature in low_adoption_features:
            feature_name = feature.get("feature_name", "")

            # Find matching knowledge articles
            relevant_articles = [
                a
                for a in knowledge_articles
                if feature_name.lower() in a.get("title", "").lower()
                or feature_name.lower() in a.get("content", "").lower()
                or "adoption" in a.get("category", "").lower()
            ]

            if relevant_articles:
                # Use best matching article
                best_article = max(
                    relevant_articles, key=lambda x: x.get("relevance_score", 0.0)
                )

                # Generate recommendation text from knowledge article
                text_description = self._generate_adoption_text(
                    feature_name, best_article, feature.get("usage_count", 0)
                )

                # Calculate confidence based on knowledge relevance and usage clarity
                confidence = self._calculate_recommendation_confidence(
                    best_article.get("relevance_score", 0.0),
                    feature.get("usage_count", 0),
                    sentiment_score,
                )

                recommendations.append(
                    {
                        "recommendation_id": str(uuid.uuid4()),
                        "customer_id": str(customer_id),
                        "recommendation_type": RecommendationType.ADOPTION.value,
                        "text_description": text_description,
                        "confidence_score": confidence,
                        "data_sources": [
                            {
                                "source_type": "FabricIQ",
                                "source_id": feature.get("usage_id", ""),
                                "description": f"Usage data for {feature_name}",
                            },
                            {
                                "source_type": "FoundryIQ",
                                "source_id": best_article.get("article_id", ""),
                                "description": best_article.get("title", ""),
                            },
                        ],
                        "reasoning_chain": {
                            "retrieval_agent": {
                                "feature": feature_name,
                                "current_usage": feature.get("usage_count", 0),
                                "intensity": feature.get("intensity_score", "None"),
                            },
                            "reasoning_agent": {
                                "rationale": f"Low usage of {feature_name} presents adoption opportunity",
                                "knowledge_match": best_article.get("title", ""),
                            },
                        },
                    }
                )

        # Sort by confidence descending
        recommendations.sort(key=lambda x: x["confidence_score"], reverse=True)

        return recommendations

    async def _generate_upsell_recommendations(
        self,
        customer_id: UUID,
        usage_data: list[dict[str, Any]],
        knowledge_articles: list[dict[str, Any]],
        sentiment_score: float,
    ) -> list[dict[str, Any]]:
        """
        Generate upsell recommendation candidates.

        Identifies high-usage features that indicate readiness for premium features
        or higher tiers.

        Args:
            customer_id: Target customer identifier
            usage_data: List of usage data dictionaries
            knowledge_articles: List of knowledge article dictionaries
            sentiment_score: Customer sentiment score

        Returns:
            List of upsell recommendation candidates
        """
        recommendations = []

        # Identify high-adoption features (High intensity)
        high_adoption_features = [
            u for u in usage_data if u.get("intensity_score") == "High"
        ]

        # Find upsell-related knowledge articles
        upsell_articles = [
            a
            for a in knowledge_articles
            if "upsell" in a.get("category", "").lower()
            or "enterprise" in a.get("title", "").lower()
            or "premium" in a.get("content", "").lower()
        ]

        if high_adoption_features and upsell_articles:
            # Generate upsell recommendations based on high usage patterns
            for article in upsell_articles[:3]:  # Max 3 upsell opportunities
                # Use top high-usage features as evidence
                top_features = high_adoption_features[:2]
                feature_names = [f.get("feature_name", "") for f in top_features]

                text_description = self._generate_upsell_text(
                    feature_names, article, sentiment_score
                )

                confidence = self._calculate_recommendation_confidence(
                    article.get("relevance_score", 0.0),
                    sum(f.get("usage_count", 0) for f in top_features),
                    sentiment_score,
                )

                recommendations.append(
                    {
                        "recommendation_id": str(uuid.uuid4()),
                        "customer_id": str(customer_id),
                        "recommendation_type": RecommendationType.UPSELL.value,
                        "text_description": text_description,
                        "confidence_score": confidence,
                        "data_sources": [
                            {
                                "source_type": "FabricIQ",
                                "source_id": "usage_aggregate",
                                "description": f"High usage of {', '.join(feature_names)}",
                            },
                            {
                                "source_type": "FoundryIQ",
                                "source_id": article.get("article_id", ""),
                                "description": article.get("title", ""),
                            },
                        ],
                        "reasoning_chain": {
                            "retrieval_agent": {
                                "high_usage_features": feature_names,
                                "usage_intensity": "High",
                            },
                            "reasoning_agent": {
                                "rationale": "High feature engagement indicates readiness for premium offerings",
                                "knowledge_match": article.get("title", ""),
                            },
                        },
                    }
                )

        return recommendations

    def _generate_adoption_text(
        self, feature_name: str, article: dict[str, Any], current_usage: int
    ) -> str:
        """
        Generate human-readable adoption recommendation text.

        Args:
            feature_name: Name of underutilized feature
            article: Knowledge article with best practices
            current_usage: Current usage count

        Returns:
            Recommendation text string
        """
        # Extract key insight from article content (first sentence)
        content = article.get("content", "")
        insight = content.split(".")[0] if content else ""

        if current_usage == 0:
            return (
                f"Enable '{feature_name}' feature to unlock new capabilities. "
                f"{insight}. This feature is currently not activated for your account."
            )
        else:
            return (
                f"Increase usage of '{feature_name}' to maximize value. "
                f"Your team has used it {current_usage} times recently. "
                f"{insight}."
            )

    def _generate_upsell_text(
        self, feature_names: list[str], article: dict[str, Any], sentiment_score: float
    ) -> str:
        """
        Generate human-readable upsell recommendation text.

        Args:
            feature_names: List of high-usage features
            article: Knowledge article about upsell opportunity
            sentiment_score: Customer sentiment score

        Returns:
            Recommendation text string
        """
        # Extract key benefit from article
        content = article.get("content", "")
        benefit = content.split(".")[0] if content else ""

        features_str = " and ".join(feature_names)

        return (
            f"Based on your high usage of {features_str}, consider upgrading to unlock advanced capabilities. "
            f"{benefit}. Your current engagement level indicates strong ROI potential."
        )

    def _filter_past_recommendations(
        self,
        recommendations: list[dict[str, Any]],
        past_recommendations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Filter out duplicate or recently declined recommendations per FR-014.

        Checks past recommendations (from T055) to avoid suggesting:
        1. Recently declined recommendations (within 90 days)
        2. Pending recommendations (not yet delivered)
        3. Recently accepted recommendations (within 30 days)

        For older declined recommendations (>90 days), allows re-suggesting with
        updated reasoning if customer context has changed significantly.

        Args:
            recommendations: List of new recommendation candidates
            past_recommendations: Historical recommendations from last 12 months

        Returns:
            Filtered list of recommendations without duplicates
        """
        from datetime import datetime, timedelta

        filtered = []
        now = datetime.utcnow()

        # Build index of past recommendations by text similarity
        past_by_text = {}
        for past_rec in past_recommendations:
            text = past_rec.get("recommendation_text", "").lower().strip()
            outcome = past_rec.get("outcome_status", "Pending")
            outcome_timestamp = past_rec.get("outcome_timestamp")

            # Parse outcome timestamp
            days_since_outcome = None
            if outcome_timestamp:
                try:
                    outcome_dt = datetime.fromisoformat(outcome_timestamp.replace("Z", "+00:00"))
                    days_since_outcome = (now - outcome_dt).days
                except Exception:
                    pass

            past_by_text[text] = {
                "outcome": outcome,
                "days_since_outcome": days_since_outcome,
                "full_rec": past_rec
            }

        for rec in recommendations:
            text = rec.get("text_description", "").lower().strip()

            # Check for similar past recommendation
            if text in past_by_text:
                past = past_by_text[text]
                outcome = past["outcome"]
                days_since = past["days_since_outcome"]

                # Rule 1: Filter if recently declined (within 90 days)
                if outcome == "Declined" and days_since is not None and days_since < 90:
                    logger.info(
                        f"Filtering recommendation due to recent decline ({days_since} days ago): {text[:50]}..."
                    )
                    continue

                # Rule 2: Filter if still pending delivery
                if outcome == "Pending":
                    logger.info(
                        f"Filtering recommendation as it's already pending: {text[:50]}..."
                    )
                    continue

                # Rule 3: Filter if recently accepted (within 30 days)
                if outcome == "Accepted" and days_since is not None and days_since < 30:
                    logger.info(
                        f"Filtering recommendation due to recent acceptance ({days_since} days ago): {text[:50]}..."
                    )
                    continue

                # Rule 4: Allow re-suggesting if declined long ago (>90 days) or accepted long ago (>30 days)
                # Add re-suggestion reasoning to metadata
                if outcome == "Declined" and days_since is not None and days_since >= 90:
                    rec["reasoning_chain"]["re_suggestion"] = {
                        "previous_outcome": "Declined",
                        "days_since_previous": days_since,
                        "rationale": "Re-suggesting after 90+ days as customer context may have changed"
                    }
                    logger.info(
                        f"Re-suggesting previously declined recommendation after {days_since} days: {text[:50]}..."
                    )

            filtered.append(rec)

        logger.info(
            f"Filtered {len(recommendations) - len(filtered)} duplicate/declined recommendations"
        )
        return filtered

    def _calculate_recommendation_confidence(
        self, knowledge_relevance: float, usage_count: int, sentiment_score: float
    ) -> float:
        """
        Calculate confidence score for a recommendation.

        Args:
            knowledge_relevance: Relevance score from knowledge article (0-1)
            usage_count: Current usage count for feature
            sentiment_score: Customer sentiment score (-1 to 1)

        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Component 1: Knowledge relevance (0-0.4)
        knowledge_score = knowledge_relevance * 0.4

        # Component 2: Usage clarity (0-0.3)
        usage_score = min(usage_count / 100.0, 0.3)

        # Component 3: Sentiment boost/penalty (0-0.3)
        # Positive sentiment boosts confidence, negative reduces it
        sentiment_adjustment = (sentiment_score + 1.0) / 2.0  # Map [-1,1] to [0,1]
        sentiment_score_contrib = sentiment_adjustment * 0.3

        confidence = knowledge_score + usage_score + sentiment_score_contrib
        return min(confidence, 1.0)  # Cap at 1.0

    def _apply_sentiment_filter(
        self,
        recommendations: list[dict[str, Any]],
        sentiment_score: float,
        sentiment_factors: list[str],
    ) -> list[dict[str, Any]]:
        """
        Apply sentiment-aware filtering per FR-015.

        Filters out upsell recommendations if customer sentiment is negative
        or if there are recent unresolved issues.

        Args:
            recommendations: List of recommendation candidates
            sentiment_score: Customer sentiment score (-1 to 1)
            sentiment_factors: List of sentiment factors

        Returns:
            Filtered list of recommendations
        """
        filtered = []

        for rec in recommendations:
            rec_type = rec.get("recommendation_type")

            # FR-015: Block upsell if sentiment is negative
            if rec_type == RecommendationType.UPSELL.value:
                if sentiment_score < -0.2:
                    logger.info(
                        f"Filtering upsell recommendation due to negative sentiment: {sentiment_score:.2f}"
                    )
                    continue

                # Also block if there are unresolved issues
                if any(
                    "unresolved" in factor or "escalation" in factor
                    for factor in sentiment_factors
                ):
                    logger.info(
                        f"Filtering upsell recommendation due to unresolved issues"
                    )
                    continue

            # Adoption recommendations always allowed (helps address negative sentiment)
            filtered.append(rec)

        return filtered
