"""
Recommendation model.

AI-generated suggestion for adoption or upsell.
Mapped to Cosmos DB 'recommendations' container with partition key /customer_id.
Includes state machine validation for outcome status transitions.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class RecommendationType(str, Enum):
    """Type of recommendation."""

    ADOPTION = "Adoption"
    UPSELL = "Upsell"


class OutcomeStatus(str, Enum):
    """Status of recommendation outcome."""

    PENDING = "Pending"
    DELIVERED = "Delivered"
    ACCEPTED = "Accepted"
    DECLINED = "Declined"
    EXCLUDED = "Excluded"


class DataSource(BaseModel):
    """
    Reference to a data source used in recommendation generation.

    Attributes:
        source_type: Type of source (e.g., "FabricIQ", "FoundryIQ")
        source_id: Identifier within the source system
        description: Human-readable description of what was retrieved
    """

    source_type: str = Field(
        ...,
        description="Type of source (e.g., 'FabricIQ', 'FoundryIQ')",
    )
    source_id: str = Field(
        ...,
        description="Identifier within the source system",
    )
    description: str = Field(
        ...,
        description="Human-readable description",
    )


class Recommendation(BaseModel):
    """
    Recommendation entity model.

    Attributes:
        recommendation_id: Unique recommendation identifier (UUID format)
        customer_id: Target customer (foreign key to Customer.account_id, partition key)
        recommendation_type: Type of recommendation
        text_description: Human-readable recommendation text (max 1000 chars, passed through Content Safety)
        reasoning_chain: Structured agent reasoning (JSON with agent contributions)
        confidence_score: AI confidence (0.0 to 1.0)
        data_sources: References to Fabric IQ, Foundry IQ sources used
        generation_timestamp: When recommendation was generated (system-managed)
        outcome_status: Current status in state machine
        delivered_by_agent_id: Support agent who delivered to customer (optional)
        outcome_timestamp: When outcome was recorded (optional)
        created_at: Record creation timestamp (system-managed)
        updated_at: Last modification timestamp (system-managed)
    """

    recommendation_id: UUID = Field(
        ...,
        description="Unique recommendation identifier",
    )
    customer_id: UUID = Field(
        ...,
        description="Target customer (partition key)",
    )
    recommendation_type: RecommendationType = Field(
        ...,
        description="Type of recommendation",
    )
    text_description: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Human-readable recommendation text",
    )
    reasoning_chain: dict[str, Any] = Field(
        ...,
        description="Structured agent reasoning (JSON)",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="AI confidence score",
    )
    data_sources: list[DataSource] = Field(
        ...,
        min_length=1,
        description="References to sources used",
    )
    generation_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When recommendation was generated",
    )
    outcome_status: OutcomeStatus = Field(
        default=OutcomeStatus.PENDING,
        description="Current status in state machine",
    )
    delivered_by_agent_id: Optional[str] = Field(
        None,
        description="Support agent who delivered to customer",
    )
    outcome_timestamp: Optional[datetime] = Field(
        None,
        description="When outcome was recorded",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Record creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last modification timestamp",
    )

    @field_validator("text_description")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        """Validate text_description is not empty or whitespace only."""
        if not v.strip():
            raise ValueError("text_description cannot be empty or whitespace")
        return v.strip()

    @field_validator("reasoning_chain")
    @classmethod
    def validate_reasoning_chain(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate reasoning_chain is not empty."""
        if not v:
            raise ValueError("reasoning_chain cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_state_transitions(self) -> "Recommendation":
        """
        Validate state transitions per data-model.md.

        Valid transitions:
        - Pending → Delivered (agent shows to customer)
        - Delivered → Accepted (customer agrees)
        - Delivered → Declined (customer rejects)
        - Declined → Excluded (system stops suggesting)

        Rules:
        - If outcome_status is DELIVERED, ACCEPTED, DECLINED, or EXCLUDED,
          delivered_by_agent_id and outcome_timestamp must be set
        - Cannot go from PENDING directly to ACCEPTED, DECLINED, or EXCLUDED
        """
        status = self.outcome_status

        # Delivered, Accepted, Declined, Excluded require delivered_by_agent_id
        if status in [
            OutcomeStatus.DELIVERED,
            OutcomeStatus.ACCEPTED,
            OutcomeStatus.DECLINED,
            OutcomeStatus.EXCLUDED,
        ]:
            if not self.delivered_by_agent_id:
                raise ValueError(
                    f"delivered_by_agent_id required when outcome_status is {status.value}"
                )
            if not self.outcome_timestamp:
                raise ValueError(
                    f"outcome_timestamp required when outcome_status is {status.value}"
                )

        return self

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "recommendation_id": "880e8400-e29b-41d4-a716-446655440003",
                "customer_id": "550e8400-e29b-41d4-a716-446655440000",
                "recommendation_type": "Adoption",
                "text_description": "Enable 'Advanced Reporting' feature to gain deeper insights into supply chain bottlenecks. Your team has viewed reports 142 times this month but hasn't activated the advanced analytics module.",
                "reasoning_chain": {
                    "retrieval_agent": {"usage_trend": "high_basic_usage", "knowledge_match": "reporting_best_practices"},
                    "sentiment_agent": {"score": 0.8, "factors": ["positive_support_history"]},
                    "reasoning_agent": {"rationale": "High engagement with basic reporting indicates readiness for advanced features"},
                    "validation_agent": {"duplicate_check": "passed", "content_safety": "approved"},
                },
                "confidence_score": 0.87,
                "data_sources": [
                    {
                        "source_type": "FabricIQ",
                        "source_id": "usage_trend_2025_w50",
                        "description": "Weekly usage summary for Dashboard Analytics",
                    },
                    {
                        "source_type": "FoundryIQ",
                        "source_id": "kb_article_1234",
                        "description": "Best practices for advanced reporting adoption",
                    },
                ],
                "generation_timestamp": "2025-12-22T10:00:00Z",
                "outcome_status": "Pending",
                "delivered_by_agent_id": None,
                "outcome_timestamp": None,
            }
        }
