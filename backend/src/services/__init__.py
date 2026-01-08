"""
Services package for external integrations and business logic.

This package contains clients for Azure services and external systems:
- fabric_client: Fabric IQ semantic layer for usage data
- foundry_client: Foundry IQ knowledge base for RAG patterns
- content_safety: Azure AI Content Safety for validation
- customer_service: Customer search and profile retrieval
- recommendation_service: Recommendation generation and caching
"""

from .fabric_client import FabricIQClient
from .foundry_client import FoundryIQClient, KnowledgeArticle
from .content_safety import ContentSafetyService, ContentSafetyResult
from .customer_service import CustomerService
from .recommendation_service import RecommendationService

__all__ = [
    "FabricIQClient",
    "FoundryIQClient",
    "KnowledgeArticle",
    "ContentSafetyService",
    "ContentSafetyResult",
    "CustomerService",
    "RecommendationService",
]
