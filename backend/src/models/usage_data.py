"""
UsageData model.

Time-series data representing customer feature usage from Fabric IQ.
This model represents aggregated usage data, not stored in Cosmos DB.
Data is queried from Fabric IQ semantic layer on-demand.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class IntensityScore(str, Enum):
    """Usage intensity levels."""

    NONE = "None"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class UsageData(BaseModel):
    """
    Usage data entity model.

    Attributes:
        usage_id: Unique usage record identifier (UUID format)
        customer_id: Associated customer (foreign key to Customer.account_id)
        feature_name: Name of feature used (max 100 characters)
        usage_count: Number of times feature used in time window (non-negative)
        last_used_timestamp: Most recent usage timestamp (cannot be in future)
        intensity_score: Usage intensity classification
        time_window: Aggregation period (e.g., "daily", "weekly")
        recorded_at: When this usage record was created (system-managed)
    """

    usage_id: UUID = Field(
        ...,
        description="Unique usage record identifier",
    )
    customer_id: UUID = Field(
        ...,
        description="Associated customer (foreign key)",
    )
    feature_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of feature used",
    )
    usage_count: int = Field(
        ...,
        ge=0,
        description="Number of times feature used in time window",
    )
    last_used_timestamp: datetime = Field(
        ...,
        description="Most recent usage timestamp",
    )
    intensity_score: IntensityScore = Field(
        ...,
        description="Usage intensity classification",
    )
    time_window: str = Field(
        ...,
        description="Aggregation period (e.g., 'daily', 'weekly')",
    )
    recorded_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this usage record was created",
    )

    @field_validator("last_used_timestamp")
    @classmethod
    def validate_timestamp_not_future(cls, v: datetime) -> datetime:
        """Validate last_used_timestamp is not in the future."""
        if v > datetime.utcnow():
            raise ValueError("last_used_timestamp cannot be in the future")
        return v

    @field_validator("feature_name")
    @classmethod
    def feature_name_not_empty(cls, v: str) -> str:
        """Validate feature_name is not empty or whitespace only."""
        if not v.strip():
            raise ValueError("feature_name cannot be empty or whitespace")
        return v.strip()

    @field_validator("time_window")
    @classmethod
    def time_window_not_empty(cls, v: str) -> str:
        """Validate time_window is not empty or whitespace only."""
        if not v.strip():
            raise ValueError("time_window cannot be empty or whitespace")
        return v.strip()

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "usage_id": "660e8400-e29b-41d4-a716-446655440001",
                "customer_id": "550e8400-e29b-41d4-a716-446655440000",
                "feature_name": "Dashboard Analytics",
                "usage_count": 142,
                "last_used_timestamp": "2025-12-15T14:30:00Z",
                "intensity_score": "High",
                "time_window": "weekly",
                "recorded_at": "2025-12-22T08:00:00Z",
            }
        }
