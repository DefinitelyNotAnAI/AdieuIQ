"""
Sentiment Analysis Agent for multi-agent orchestration.

This agent analyzes customer interaction history to determine sentiment
and identify factors that should influence recommendation generation.

Constitutional Compliance:
- Part of Azure AI Foundry SDK orchestration (Constitutional Principle V)
- Implements sentiment-aware filtering per FR-015
- Runs in parallel with Retrieval Agent to optimize latency
"""

import asyncio
import logging
from typing import Any
from uuid import UUID

from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential

from ...core.observability import get_tracer
from ...models.interaction_event import InteractionEvent

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class SentimentAgent:
    """
    Sentiment Analysis Agent for customer interaction analysis.

    Analyzes historical interactions (tickets, chats, calls) to calculate
    sentiment score and identify factors that influence recommendation suitability.

    This agent runs in parallel with Retrieval Agent (T028) in the orchestration workflow.
    """

    def __init__(self, credential: TokenCredential | None = None):
        """
        Initialize Sentiment Agent.

        Args:
            credential: Azure credential for Cosmos DB access (optional, uses DefaultAzureCredential if None)
        """
        self.credential = credential or DefaultAzureCredential()
        logger.info("SentimentAgent initialized")

    async def run(
        self, customer_id: UUID, days: int = 90
    ) -> dict[str, Any]:
        """
        Execute sentiment analysis agent workflow.

        Analyzes customer interaction history to calculate sentiment score
        and identify factors (positive/negative). Used by Reasoning Agent (T030)
        to apply sentiment-aware filtering per FR-015.

        Args:
            customer_id: Target customer identifier
            days: Number of days to look back for interactions (default 90)

        Returns:
            Dictionary containing:
            - sentiment_score: Overall sentiment (-1.0 to +1.0, where -1 is very negative)
            - sentiment_factors: List of sentiment influencing factors
            - interaction_count: Number of interactions analyzed
            - recent_issues: List of recent unresolved issues
            - confidence: Confidence in sentiment analysis (0.0 to 1.0)
            - execution_time_ms: Agent execution time

        Raises:
            ValueError: If customer_id is invalid or days is not positive
        """
        if days <= 0:
            raise ValueError("days must be positive")

        with tracer.start_as_current_span("sentiment_agent.run") as span:
            span.set_attribute("customer_id", str(customer_id))
            span.set_attribute("days", days)

            start_time = asyncio.get_event_loop().time()

            try:
                # Phase 1: Retrieve interaction history from Cosmos DB
                interactions = await self._get_interaction_history(customer_id, days)

                if not interactions:
                    # No interaction history - neutral sentiment with low confidence
                    logger.info(
                        f"No interaction history found for customer {customer_id}"
                    )
                    return self._build_neutral_result(customer_id, start_time)

                # Phase 2: Calculate sentiment metrics
                sentiment_score = self._calculate_sentiment_score(interactions)
                sentiment_factors = self._identify_sentiment_factors(interactions)
                recent_issues = self._extract_recent_issues(interactions)
                confidence = self._calculate_confidence(interactions)

                # Calculate execution time
                end_time = asyncio.get_event_loop().time()
                execution_time_ms = int((end_time - start_time) * 1000)

                result = {
                    "sentiment_score": sentiment_score,
                    "sentiment_factors": sentiment_factors,
                    "interaction_count": len(interactions),
                    "recent_issues": recent_issues,
                    "confidence": confidence,
                    "execution_time_ms": execution_time_ms,
                }

                span.set_attribute("sentiment_score", sentiment_score)
                span.set_attribute("confidence", confidence)
                span.set_attribute("execution_time_ms", execution_time_ms)
                span.set_attribute("interaction_count", len(interactions))

                logger.info(
                    f"SentimentAgent completed: customer_id={customer_id}, "
                    f"sentiment={sentiment_score:.2f}, confidence={confidence:.2f}, "
                    f"execution_time={execution_time_ms}ms"
                )

                return result

            except Exception as e:
                logger.error(f"SentimentAgent failed: {e}", exc_info=True)
                span.set_attribute("error", str(e))
                raise

    async def _get_interaction_history(
        self, customer_id: UUID, days: int
    ) -> list[InteractionEvent]:
        """
        Retrieve interaction history from Cosmos DB.

        Implementation placeholder - will query Cosmos DB 'interaction-events' container
        with partition key /customer_id and filter by timestamp.

        Args:
            customer_id: Target customer identifier
            days: Number of days to look back

        Returns:
            List of InteractionEvent objects

        Raises:
            RuntimeError: If Cosmos DB query fails
        """
        # TODO: Implement actual Cosmos DB query
        # Reference: azure.cosmos.CosmosClient
        #
        # Expected implementation:
        # 1. Query interaction-events container with customer_id partition key
        # 2. Filter by timestamp (past N days)
        # 3. Order by timestamp descending
        # 4. Parse results into InteractionEvent models
        #
        # For now, return mock data for local development
        import os
        from datetime import datetime, timedelta
        import uuid

        if os.getenv("ENV") == "local":
            # Mock data: Mix of positive and negative interactions
            now = datetime.utcnow()
            return [
                InteractionEvent(
                    event_id=uuid.uuid4(),
                    customer_id=customer_id,
                    event_type="Ticket",
                    timestamp=now - timedelta(days=5),
                    agent_id="agent-42",
                    sentiment_score=-0.3,
                    topics_discussed=["API Integration", "SSL Certificate"],
                    resolution_status="Resolved",
                    duration_seconds=1200,
                ),
                InteractionEvent(
                    event_id=uuid.uuid4(),
                    customer_id=customer_id,
                    event_type="Chat",
                    timestamp=now - timedelta(days=15),
                    agent_id="agent-23",
                    sentiment_score=0.7,
                    topics_discussed=["Feature Request", "Dashboard"],
                    resolution_status="Resolved",
                    duration_seconds=600,
                ),
                InteractionEvent(
                    event_id=uuid.uuid4(),
                    customer_id=customer_id,
                    event_type="Call",
                    timestamp=now - timedelta(days=30),
                    agent_id="agent-15",
                    sentiment_score=0.2,
                    topics_discussed=["Training", "Onboarding"],
                    resolution_status="Resolved",
                    duration_seconds=1800,
                ),
            ]
        else:
            raise NotImplementedError(
                "Cosmos DB interaction history query pending production integration. "
                "Implement CosmosClient query for interaction-events container."
            )

    def _calculate_sentiment_score(
        self, interactions: list[InteractionEvent]
    ) -> float:
        """
        Calculate overall sentiment score from interactions.

        Weighs recent interactions more heavily (exponential decay).

        Args:
            interactions: List of interaction events

        Returns:
            Sentiment score (-1.0 to +1.0)
        """
        if not interactions:
            return 0.0

        # Sort by timestamp descending (most recent first)
        sorted_interactions = sorted(
            interactions, key=lambda x: x.timestamp, reverse=True
        )

        # Calculate weighted average with exponential decay
        # Recent interactions have weight ~1.0, older interactions decay to ~0.1
        total_weight = 0.0
        weighted_sum = 0.0

        for i, interaction in enumerate(sorted_interactions):
            weight = 0.9 ** i  # Exponential decay: 1.0, 0.9, 0.81, 0.73, ...
            weighted_sum += interaction.sentiment_score * weight
            total_weight += weight

        sentiment_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        return max(-1.0, min(1.0, sentiment_score))  # Clamp to [-1.0, 1.0]

    def _identify_sentiment_factors(
        self, interactions: list[InteractionEvent]
    ) -> list[str]:
        """
        Identify key factors influencing sentiment.

        Args:
            interactions: List of interaction events

        Returns:
            List of sentiment factors (e.g., "recent_escalation", "positive_feedback")
        """
        factors = []

        # Factor 1: Recent unresolved issues
        recent_unresolved = [
            i for i in interactions if i.resolution_status != "Resolved"
        ]
        if recent_unresolved:
            factors.append(
                f"unresolved_issues_count_{len(recent_unresolved)}"
            )

        # Factor 2: Recent escalations
        recent_escalations = [
            i for i in interactions if i.resolution_status == "Escalated"
        ]
        if recent_escalations:
            factors.append("recent_escalation")

        # Factor 3: Positive trend (improving sentiment over time)
        if len(interactions) >= 3:
            sorted_interactions = sorted(interactions, key=lambda x: x.timestamp)
            recent_avg = sum(i.sentiment_score for i in sorted_interactions[-3:]) / 3
            older_avg = sum(i.sentiment_score for i in sorted_interactions[:3]) / 3
            if recent_avg > older_avg + 0.2:
                factors.append("improving_sentiment")
            elif recent_avg < older_avg - 0.2:
                factors.append("declining_sentiment")

        # Factor 4: High interaction frequency
        if len(interactions) > 10:
            factors.append("high_interaction_frequency")

        # Factor 5: Overall sentiment classification
        avg_sentiment = sum(i.sentiment_score for i in interactions) / len(
            interactions
        )
        if avg_sentiment > 0.5:
            factors.append("positive_support_history")
        elif avg_sentiment < -0.3:
            factors.append("negative_support_history")

        return factors

    def _extract_recent_issues(
        self, interactions: list[InteractionEvent]
    ) -> list[dict[str, Any]]:
        """
        Extract recent unresolved or escalated issues.

        Args:
            interactions: List of interaction events

        Returns:
            List of issue dictionaries with topic and status
        """
        issues = []

        # Get unresolved or escalated interactions from last 30 days
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=30)

        for interaction in interactions:
            if interaction.timestamp > cutoff_date and interaction.resolution_status in [
                "Pending",
                "Escalated",
            ]:
                issues.append(
                    {
                        "event_id": str(interaction.event_id),
                        "topics": interaction.topics_discussed or [],
                        "status": interaction.resolution_status.value,
                        "timestamp": interaction.timestamp.isoformat(),
                    }
                )

        return issues

    def _calculate_confidence(self, interactions: list[InteractionEvent]) -> float:
        """
        Calculate confidence in sentiment analysis.

        Confidence is higher when:
        - More interactions are available
        - Interactions are recent
        - Sentiment scores are consistent (low variance)

        Args:
            interactions: List of interaction events

        Returns:
            Confidence score (0.0 to 1.0)
        """
        if not interactions:
            return 0.0

        # Component 1: Sample size (0-0.5)
        sample_size_score = min(len(interactions) / 20.0, 0.5)

        # Component 2: Recency (0-0.3)
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        recent_count = sum(
            1
            for i in interactions
            if (now - i.timestamp) < timedelta(days=30)
        )
        recency_score = min(recent_count / 10.0, 0.3)

        # Component 3: Consistency (0-0.2)
        # Low variance in sentiment scores = high confidence
        if len(interactions) > 1:
            scores = [i.sentiment_score for i in interactions]
            avg = sum(scores) / len(scores)
            variance = sum((s - avg) ** 2 for s in scores) / len(scores)
            # Variance of 0 = perfect consistency (score 0.2)
            # Variance of 1 = high inconsistency (score 0.0)
            consistency_score = max(0.0, 0.2 - variance * 0.2)
        else:
            consistency_score = 0.1

        confidence = sample_size_score + recency_score + consistency_score
        return min(confidence, 1.0)  # Cap at 1.0

    def _build_neutral_result(
        self, customer_id: UUID, start_time: float
    ) -> dict[str, Any]:
        """
        Build neutral result when no interaction history exists.

        Args:
            customer_id: Target customer identifier
            start_time: Agent start time

        Returns:
            Neutral sentiment result dictionary
        """
        end_time = asyncio.get_event_loop().time()
        execution_time_ms = int((end_time - start_time) * 1000)

        return {
            "sentiment_score": 0.0,
            "sentiment_factors": ["no_interaction_history"],
            "interaction_count": 0,
            "recent_issues": [],
            "confidence": 0.0,
            "execution_time_ms": execution_time_ms,
        }
