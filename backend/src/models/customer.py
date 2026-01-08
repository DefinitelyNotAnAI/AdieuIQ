"""
Customer model.

Represents a business account in the system.
Mapped to Cosmos DB 'customers' container with partition key /account_id.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class IndustrySegment(str, Enum):
    """Industry classification for customers."""

    TECHNOLOGY = "Technology"
    HEALTHCARE = "Healthcare"
    FINANCE = "Finance"
    RETAIL = "Retail"
    MANUFACTURING = "Manufacturing"
    OTHER = "Other"


class ProductTier(str, Enum):
    """Subscription tier levels."""

    BASIC = "Basic"
    PROFESSIONAL = "Professional"
    ENTERPRISE = "Enterprise"


class Customer(BaseModel):
    """
    Customer entity model.

    Attributes:
        account_id: Unique customer identifier (UUID format)
        company_name: Customer company name (max 200 characters)
        industry_segment: Industry classification
        product_tier: Subscription tier level
        subscription_start_date: When customer became active
        current_products: List of currently subscribed products (at least one required)
        contact_email: Primary contact email (optional)
        contact_phone: Primary contact phone (optional)
        created_at: Record creation timestamp (system-managed)
        updated_at: Last modification timestamp (system-managed)
    """

    account_id: UUID = Field(
        ...,
        description="Unique customer identifier (partition key)",
    )
    company_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Customer company name",
    )
    industry_segment: IndustrySegment = Field(
        ...,
        description="Industry classification",
    )
    product_tier: ProductTier = Field(
        ...,
        description="Subscription tier level",
    )
    subscription_start_date: datetime = Field(
        ...,
        description="When customer became active",
    )
    current_products: list[str] = Field(
        ...,
        min_length=1,
        description="List of currently subscribed products",
    )
    contact_email: Optional[EmailStr] = Field(
        None,
        description="Primary contact email",
    )
    contact_phone: Optional[str] = Field(
        None,
        description="Primary contact phone",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Record creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last modification timestamp",
    )

    @field_validator("company_name")
    @classmethod
    def company_name_not_empty(cls, v: str) -> str:
        """Validate company_name is not empty or whitespace only."""
        if not v.strip():
            raise ValueError("company_name cannot be empty or whitespace")
        return v.strip()

    @field_validator("current_products")
    @classmethod
    def validate_products(cls, v: list[str]) -> list[str]:
        """Validate current_products contains at least one product."""
        if not v or len(v) == 0:
            raise ValueError("current_products must contain at least one product")
        # Remove empty strings
        products = [p.strip() for p in v if p.strip()]
        if not products:
            raise ValueError("current_products must contain at least one non-empty product")
        return products

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "account_id": "550e8400-e29b-41d4-a716-446655440000",
                "company_name": "Contoso Manufacturing",
                "industry_segment": "Manufacturing",
                "product_tier": "Enterprise",
                "subscription_start_date": "2024-01-15T00:00:00Z",
                "current_products": ["ERP Suite", "Supply Chain Analytics", "IoT Platform"],
                "contact_email": "procurement@contoso.com",
                "contact_phone": "+1-555-0100",
            }
        }
