"""
AgentContribution model.

Record of each AI agent's role in recommendation generation.
Enables explainability (FR-016) and agent orchestration debugging.
Stored as embedded documents within Recommendation for single-read performance.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AgentType(str, Enum):
    """Type of AI agent in multi-agent orchestration."""

    RETRIEVAL = "Retrieval"
    SENTIMENT = "Sentiment"
    REASONING = "Reasoning"
    VALIDATION = "Validation"


class AgentContribution(BaseModel):
    """
    Agent contribution entity model.

    Attributes:
        contribution_id: Unique contribution identifier (UUID format)
        recommendation_id: Associated recommendation (foreign key to Recommendation.recommendation_id)
        agent_type: Agent role in orchestration
        input_data: Data provided to agent (JSON)
        output_result: Agent's output (JSON)
        confidence_score: Agent's confidence (0.0 to 1.0)
        execution_time_ms: Agent execution duration in milliseconds (must be positive)
        created_at: Record creation timestamp (system-managed)
    """

    contribution_id: UUID = Field(
        ...,
        description="Unique contribution identifier",
    )
    recommendation_id: UUID = Field(
        ...,
        description="Associated recommendation (foreign key)",
    )
    agent_type: AgentType = Field(
        ...,
        description="Agent role in orchestration",
    )
    input_data: dict[str, Any] = Field(
        ...,
        description="Data provided to agent (JSON)",
    )
    output_result: dict[str, Any] = Field(
        ...,
        description="Agent's output (JSON)",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Agent's confidence score",
    )
    execution_time_ms: int = Field(
        ...,
        gt=0,
        description="Agent execution duration in milliseconds",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Record creation timestamp",
    )

    @field_validator("input_data")
    @classmethod
    def validate_input_data(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate input_data is not empty."""
        if not v:
            raise ValueError("input_data cannot be empty")
        return v

    @field_validator("output_result")
    @classmethod
    def validate_output_result(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate output_result is not empty."""
        if not v:
            raise ValueError("output_result cannot be empty")
        return v

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "contribution_id": "990e8400-e29b-41d4-a716-446655440004",
                "recommendation_id": "880e8400-e29b-41d4-a716-446655440003",
                "agent_type": "Retrieval",
                "input_data": {
                    "customer_id": "550e8400-e29b-41d4-a716-446655440000",
                    "feature_filter": "reporting",
                    "time_range": "last_30_days",
                },
                "output_result": {
                    "usage_trends": [
                        {"feature": "Dashboard Analytics", "usage_count": 142, "intensity": "High"}
                    ],
                    "knowledge_articles": [
                        {"id": "kb_article_1234", "title": "Advanced Reporting Best Practices", "relevance": 0.92}
                    ],
                },
                "confidence_score": 0.89,
                "execution_time_ms": 245,
                "created_at": "2025-12-22T10:00:00Z",
            }
        }
