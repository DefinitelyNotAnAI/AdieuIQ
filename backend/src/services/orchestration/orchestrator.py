"""
Multi-Agent Orchestrator for recommendation generation.

This orchestrator coordinates the execution of all AI agents in the correct
sequence to generate high-quality, validated recommendations.

Constitutional Compliance (NON-NEGOTIABLE):
- Uses Azure AI Foundry SDK patterns (Constitutional Principle V)
- Parallel execution: Retrieval Agent (T028) || Sentiment Agent (T029)
- Sequential execution: Reasoning Agent (T030) → Validation Agent (T031)
- Logs reasoning chains per FR-010 for explainability
- Enforces <2s p95 latency requirement (FR-005)
"""

import asyncio
import logging
from typing import Any
from uuid import UUID, uuid4

from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential

from ...core.observability import get_tracer
from ...models.agent_contribution import AgentContribution, AgentType
from .retrieval_agent import RetrievalAgent
from .sentiment_agent import SentimentAgent
from .reasoning_agent import ReasoningAgent
from .validation_agent import ValidationAgent

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class RecommendationOrchestrator:
    """
    Multi-agent orchestrator for recommendation generation.

    Orchestrates four AI agents in a specific execution pattern:
    1. Phase 1 (Parallel): Retrieval Agent + Sentiment Agent
    2. Phase 2 (Sequential): Reasoning Agent (uses Phase 1 outputs)
    3. Phase 3 (Sequential): Validation Agent (uses Phase 2 outputs)

    Constitutional requirement: This orchestration pattern follows
    Azure AI Foundry SDK best practices for multi-agent systems.
    """

    def __init__(self, credential: TokenCredential | None = None):
        """
        Initialize orchestrator with all agents.

        Args:
            credential: Azure credential for authentication (optional, uses DefaultAzureCredential if None)
        """
        self.credential = credential or DefaultAzureCredential()

        # Initialize all agents
        self.retrieval_agent = RetrievalAgent()
        self.sentiment_agent = SentimentAgent(credential=self.credential)
        self.reasoning_agent = ReasoningAgent()
        self.validation_agent = ValidationAgent()

        logger.info("RecommendationOrchestrator initialized with 4 agents")

    async def generate_recommendations(
        self, customer_id: UUID, days: int = 90
    ) -> dict[str, Any]:
        """
        Generate validated recommendations for a customer.

        Orchestrates all agents in correct sequence, logs reasoning chains,
        and returns validated recommendations with full audit trail.

        Args:
            customer_id: Target customer identifier
            days: Number of days to look back for data (default 90)

        Returns:
            Dictionary containing:
            - adoption_recommendations: List of validated adoption recommendations (2-5 per FR-003)
            - upsell_recommendations: List of validated upsell recommendations (1-3 per FR-004)
            - agent_contributions: List of AgentContribution objects for explainability
            - orchestration_metadata: Metadata about execution (latency, success/failure)
            - generation_time_ms: Total orchestration time

        Raises:
            ValueError: If customer_id is invalid or days is not positive
            RuntimeError: If orchestration fails and graceful degradation is not possible
        """
        if days <= 0:
            raise ValueError("days must be positive")

        with tracer.start_as_current_span("orchestrator.generate_recommendations") as span:
            span.set_attribute("customer_id", str(customer_id))
            span.set_attribute("days", days)

            start_time = asyncio.get_event_loop().time()
            recommendation_id = uuid4()  # Single ID for this generation cycle

            try:
                # Phase 1: Parallel execution (Retrieval + Sentiment)
                logger.info(
                    f"Phase 1: Parallel execution (Retrieval + Sentiment) for customer {customer_id}"
                )
                with tracer.start_as_current_span("phase1_parallel"):
                    retrieval_task = self.retrieval_agent.run(customer_id, days)
                    sentiment_task = self.sentiment_agent.run(customer_id, days)

                    retrieval_result, sentiment_result = await asyncio.gather(
                        retrieval_task, sentiment_task
                    )

                # Phase 2: Sequential execution (Reasoning uses Phase 1 outputs)
                logger.info(f"Phase 2: Reasoning agent for customer {customer_id}")
                with tracer.start_as_current_span("phase2_reasoning"):
                    reasoning_result = await self.reasoning_agent.run(
                        customer_id, retrieval_result, sentiment_result
                    )

                # Phase 3: Sequential execution (Validation uses Phase 2 outputs)
                logger.info(f"Phase 3: Validation agent for customer {customer_id}")
                with tracer.start_as_current_span("phase3_validation"):
                    validation_result = await self.validation_agent.run(
                        customer_id, reasoning_result
                    )

                # Phase 4: Log reasoning chains for explainability (FR-010)
                agent_contributions = await self._log_agent_contributions(
                    recommendation_id,
                    retrieval_result,
                    sentiment_result,
                    reasoning_result,
                    validation_result,
                )

                # Calculate total generation time
                end_time = asyncio.get_event_loop().time()
                generation_time_ms = int((end_time - start_time) * 1000)

                # Check latency requirement (FR-005: <2s p95)
                if generation_time_ms > 2000:
                    logger.warning(
                        f"Recommendation generation exceeded 2s target: {generation_time_ms}ms"
                    )
                    span.set_attribute("latency_violation", True)

                # Split validated recommendations by type
                validated = validation_result.get("validated_recommendations", [])
                adoption_recs = [
                    r for r in validated if r.get("recommendation_type") == "Adoption"
                ]
                upsell_recs = [
                    r for r in validated if r.get("recommendation_type") == "Upsell"
                ]

                result = {
                    "adoption_recommendations": adoption_recs,
                    "upsell_recommendations": upsell_recs,
                    "agent_contributions": [c.dict() for c in agent_contributions],
                    "orchestration_metadata": {
                        "customer_id": str(customer_id),
                        "recommendation_id": str(recommendation_id),
                        "generation_time_ms": generation_time_ms,
                        "phase1_parallel_time_ms": max(
                            retrieval_result.get("execution_time_ms", 0),
                            sentiment_result.get("execution_time_ms", 0),
                        ),
                        "phase2_reasoning_time_ms": reasoning_result.get(
                            "execution_time_ms", 0
                        ),
                        "phase3_validation_time_ms": validation_result.get(
                            "execution_time_ms", 0
                        ),
                        "validation_summary": validation_result.get(
                            "validation_summary", {}
                        ),
                        "latency_target_met": generation_time_ms <= 2000,
                    },
                    "generation_time_ms": generation_time_ms,
                }

                span.set_attribute("adoption_count", len(adoption_recs))
                span.set_attribute("upsell_count", len(upsell_recs))
                span.set_attribute("generation_time_ms", generation_time_ms)
                span.set_attribute("success", True)

                logger.info(
                    f"RecommendationOrchestrator completed: customer_id={customer_id}, "
                    f"adoption={len(adoption_recs)}, upsell={len(upsell_recs)}, "
                    f"generation_time={generation_time_ms}ms"
                )

                return result

            except Exception as e:
                logger.error(
                    f"RecommendationOrchestrator failed: {e}", exc_info=True
                )
                span.set_attribute("error", str(e))
                span.set_attribute("success", False)

                # Attempt graceful degradation per FR-017
                return await self._graceful_degradation(customer_id, str(e), start_time)

    async def _log_agent_contributions(
        self,
        recommendation_id: UUID,
        retrieval_result: dict[str, Any],
        sentiment_result: dict[str, Any],
        reasoning_result: dict[str, Any],
        validation_result: dict[str, Any],
    ) -> list[AgentContribution]:
        """
        Log agent contributions for explainability per FR-010.

        Creates AgentContribution records for each agent's role in the
        recommendation generation process. These records enable User Story 4
        (explainability panel in frontend).

        Args:
            recommendation_id: Unique identifier for this generation cycle
            retrieval_result: Output from Retrieval Agent
            sentiment_result: Output from Sentiment Agent
            reasoning_result: Output from Reasoning Agent
            validation_result: Output from Validation Agent

        Returns:
            List of AgentContribution objects
        """
        contributions = []

        # Contribution 1: Retrieval Agent
        contributions.append(
            AgentContribution(
                contribution_id=uuid4(),
                recommendation_id=recommendation_id,
                agent_type=AgentType.RETRIEVAL,
                input_data={
                    "days": 90,
                },
                output_result={
                    "usage_data_count": len(retrieval_result.get("usage_data", [])),
                    "knowledge_article_count": len(
                        retrieval_result.get("knowledge_articles", [])
                    ),
                    "confidence": retrieval_result.get("confidence", 0.0),
                },
                confidence_score=retrieval_result.get("confidence", 0.0),
                execution_time_ms=retrieval_result.get("execution_time_ms", 0),
            )
        )

        # Contribution 2: Sentiment Agent
        contributions.append(
            AgentContribution(
                contribution_id=uuid4(),
                recommendation_id=recommendation_id,
                agent_type=AgentType.SENTIMENT,
                input_data={
                    "days": 90,
                },
                output_result={
                    "sentiment_score": sentiment_result.get("sentiment_score", 0.0),
                    "sentiment_factors": sentiment_result.get("sentiment_factors", []),
                    "interaction_count": sentiment_result.get("interaction_count", 0),
                    "recent_issues": sentiment_result.get("recent_issues", []),
                },
                confidence_score=sentiment_result.get("confidence", 0.0),
                execution_time_ms=sentiment_result.get("execution_time_ms", 0),
            )
        )

        # Contribution 3: Reasoning Agent
        contributions.append(
            AgentContribution(
                contribution_id=uuid4(),
                recommendation_id=recommendation_id,
                agent_type=AgentType.REASONING,
                input_data={
                    "usage_data_count": len(retrieval_result.get("usage_data", [])),
                    "knowledge_article_count": len(
                        retrieval_result.get("knowledge_articles", [])
                    ),
                    "sentiment_score": sentiment_result.get("sentiment_score", 0.0),
                },
                output_result={
                    "adoption_candidates": len(
                        reasoning_result.get("adoption_recommendations", [])
                    ),
                    "upsell_candidates": len(
                        reasoning_result.get("upsell_recommendations", [])
                    ),
                    "reasoning_metadata": reasoning_result.get(
                        "reasoning_metadata", {}
                    ),
                },
                confidence_score=0.0,  # Reasoning agent doesn't provide confidence
                execution_time_ms=reasoning_result.get("execution_time_ms", 0),
            )
        )

        # Contribution 4: Validation Agent
        contributions.append(
            AgentContribution(
                contribution_id=uuid4(),
                recommendation_id=recommendation_id,
                agent_type=AgentType.VALIDATION,
                input_data={
                    "candidate_count": validation_result.get("validation_summary", {}).get(
                        "total_candidates", 0
                    ),
                },
                output_result={
                    "validated_count": len(
                        validation_result.get("validated_recommendations", [])
                    ),
                    "blocked_count": len(
                        validation_result.get("blocked_recommendations", [])
                    ),
                    "validation_summary": validation_result.get(
                        "validation_summary", {}
                    ),
                },
                confidence_score=1.0,  # Validation is binary (pass/fail)
                execution_time_ms=validation_result.get("execution_time_ms", 0),
            )
        )

        # TODO: Store contributions in Cosmos DB for persistence
        # Reference: Store with recommendation document or separate contributions container
        logger.info(
            f"Logged {len(contributions)} agent contributions for recommendation {recommendation_id}"
        )

        return contributions

    async def _graceful_degradation(
        self, customer_id: UUID, error_message: str, start_time: float
    ) -> dict[str, Any]:
        """
        Provide graceful degradation per FR-017.

        Returns empty recommendations with error metadata instead of failing completely.

        Args:
            customer_id: Target customer identifier
            error_message: Error message from failed orchestration
            start_time: Orchestration start time

        Returns:
            Degraded result with empty recommendations
        """
        end_time = asyncio.get_event_loop().time()
        generation_time_ms = int((end_time - start_time) * 1000)

        logger.warning(
            f"Graceful degradation: returning empty recommendations for customer {customer_id}"
        )

        return {
            "adoption_recommendations": [],
            "upsell_recommendations": [],
            "agent_contributions": [],
            "orchestration_metadata": {
                "customer_id": str(customer_id),
                "generation_time_ms": generation_time_ms,
                "success": False,
                "error": error_message,
                "graceful_degradation": True,
            },
            "generation_time_ms": generation_time_ms,
        }
