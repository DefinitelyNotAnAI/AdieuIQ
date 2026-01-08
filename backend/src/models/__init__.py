"""
Data models for Customer Recommendation Engine.

This package contains Pydantic models for all entities defined in data-model.md.
Models provide validation, serialization, and type safety across the application.
"""

from .customer import Customer
from .usage_data import UsageData
from .interaction_event import InteractionEvent, EventType, ResolutionStatus
from .recommendation import (
    Recommendation,
    RecommendationType,
    OutcomeStatus,
    DataSource,
)
from .agent_contribution import AgentContribution, AgentType

__all__ = [
    "Customer",
    "UsageData",
    "InteractionEvent",
    "EventType",
    "ResolutionStatus",
    "Recommendation",
    "RecommendationType",
    "OutcomeStatus",
    "DataSource",
    "AgentContribution",
    "AgentType",
]
