"""
InteractionEvent model.

Historical support interaction record.
Mapped to Cosmos DB 'interaction-events' container with partition key /customer_id.
Data source: Fabric Real-Time Intelligence (ingested from support systems).
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EventType(str, Enum):
    """Type of customer interaction."""

    TICKET = "Ticket"
    CHAT = "Chat"
    CALL = "Call"


class ResolutionStatus(str, Enum):
    """Outcome status of interaction."""

    RESOLVED = "Resolved"
    PENDING = "Pending"
    ESCALATED = "Escalated"


class InteractionEvent(BaseModel):
    """
    Interaction event entity model.

    Attributes:
        event_id: Unique event identifier (UUID format)
        customer_id: Associated customer (foreign key to Customer.account_id, partition key)
        event_type: Type of interaction
        timestamp: When interaction occurred (cannot be in future)
        agent_id: Support agent who handled interaction (optional)
        sentiment_score: Sentiment analysis score (-1.0 to +1.0)
        topics_discussed: Extracted topics/keywords (optional)
        resolution_status: Outcome status
        duration_seconds: Interaction duration in seconds (optional, must be positive)
        created_at: Record creation timestamp (system-managed)
    """

    event_id: UUID = Field(
        ...,
        description="Unique event identifier",
    )
    customer_id: UUID = Field(
        ...,
        description="Associated customer (partition key)",
    )
    event_type: EventType = Field(
        ...,
        description="Type of interaction",
    )
    timestamp: datetime = Field(
        ...,
        description="When interaction occurred",
    )
    agent_id: Optional[str] = Field(
        None,
        description="Support agent who handled interaction",
    )
    sentiment_score: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Sentiment analysis score (-1.0 to +1.0)",
    )
    topics_discussed: Optional[list[str]] = Field(
        None,
        description="Extracted topics/keywords",
    )
    resolution_status: ResolutionStatus = Field(
        ...,
        description="Outcome status",
    )
    duration_seconds: Optional[int] = Field(
        None,
        gt=0,
        description="Interaction duration in seconds (must be positive)",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Record creation timestamp",
    )

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp_not_future(cls, v: datetime) -> datetime:
        """Validate timestamp is not in the future."""
        if v > datetime.utcnow():
            raise ValueError("timestamp cannot be in the future")
        return v

    @field_validator("topics_discussed")
    @classmethod
    def validate_topics(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate topics_discussed contains no empty strings."""
        if v is None:
            return v
        # Remove empty strings
        topics = [t.strip() for t in v if t.strip()]
        return topics if topics else None

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "event_id": "770e8400-e29b-41d4-a716-446655440002",
                "customer_id": "550e8400-e29b-41d4-a716-446655440000",
                "event_type": "Ticket",
                "timestamp": "2025-12-10T10:15:00Z",
                "agent_id": "agent-42",
                "sentiment_score": -0.3,
                "topics_discussed": ["API Integration", "Authentication Issues", "SSL Certificate"],
                "resolution_status": "Resolved",
                "duration_seconds": 1200,
                "created_at": "2025-12-10T10:35:00Z",
            }
        }
