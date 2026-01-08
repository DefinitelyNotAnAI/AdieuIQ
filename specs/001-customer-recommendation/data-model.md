# Data Model: Customer Recommendation Engine

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)  
**Phase**: 1 (Design)  
**Purpose**: Define entities, relationships, and validation rules

## Entity Definitions

### Customer

Represents a business account in the system.

**Attributes**:
- `account_id` (string, PK): Unique customer identifier (UUID format)
- `company_name` (string, required): Customer company name
- `industry_segment` (enum, required): Industry classification (Technology, Healthcare, Finance, Retail, Manufacturing, Other)
- `product_tier` (enum, required): Subscription tier (Basic, Professional, Enterprise)
- `subscription_start_date` (datetime, required): When customer became active
- `current_products` (array[string], required): List of currently subscribed products
- `contact_email` (string, optional): Primary contact email
- `contact_phone` (string, optional): Primary contact phone
- `created_at` (datetime, system): Record creation timestamp
- `updated_at` (datetime, system): Last modification timestamp

**Validation Rules**:
- `account_id` must be valid UUID format
- `company_name` maximum 200 characters
- `industry_segment` must match enum values
- `product_tier` must match enum values
- `contact_email` must be valid email format if provided
- `current_products` must contain at least one product

**Relationships**:
- One-to-Many with UsageData (customer has many usage records)
- One-to-Many with InteractionEvent (customer has many interactions)
- One-to-Many with Recommendation (customer receives many recommendations)

**State Transitions**:
- Active → Inactive (subscription cancelled)
- Inactive → Active (reactivated)
- Tier upgrades/downgrades tracked in product_tier field

---

### UsageData

Time-series data representing customer feature usage from Fabric IQ.

**Attributes**:
- `usage_id` (string, PK): Unique usage record identifier (UUID format)
- `customer_id` (string, FK → Customer.account_id, required): Associated customer
- `feature_name` (string, required): Name of feature used (e.g., "Dashboard Analytics", "API Integration")
- `usage_count` (integer, required): Number of times feature used in time window
- `last_used_timestamp` (datetime, required): Most recent usage timestamp
- `intensity_score` (enum, required): Usage intensity (Low, Medium, High)
- `time_window` (string, required): Aggregation period (e.g., "daily", "weekly")
- `recorded_at` (datetime, system): When this usage record was created

**Validation Rules**:
- `customer_id` must reference valid Customer
- `feature_name` maximum 100 characters
- `usage_count` must be non-negative integer
- `intensity_score` must match enum values (Low, Medium, High)
- `last_used_timestamp` cannot be in the future

**Relationships**:
- Many-to-One with Customer (many usage records belong to one customer)

**Data Source**: Fabric IQ semantic layer (aggregated from OneLake raw telemetry)

---

### InteractionEvent

Historical support interaction record.

**Attributes**:
- `event_id` (string, PK): Unique event identifier (UUID format)
- `customer_id` (string, FK → Customer.account_id, required): Associated customer
- `event_type` (enum, required): Type of interaction (Ticket, Chat, Call)
- `timestamp` (datetime, required): When interaction occurred
- `agent_id` (string, optional): Support agent who handled interaction
- `sentiment_score` (float, required): Sentiment analysis score (-1.0 to +1.0)
- `topics_discussed` (array[string], optional): Extracted topics/keywords
- `resolution_status` (enum, required): Outcome (Resolved, Pending, Escalated)
- `duration_seconds` (integer, optional): Interaction duration in seconds
- `created_at` (datetime, system): Record creation timestamp

**Validation Rules**:
- `customer_id` must reference valid Customer
- `event_type` must match enum values
- `timestamp` cannot be in the future
- `sentiment_score` must be between -1.0 and +1.0
- `resolution_status` must match enum values
- `duration_seconds` must be positive integer if provided

**Relationships**:
- Many-to-One with Customer (many interactions belong to one customer)
- Referenced by Recommendation (for context)

**Data Source**: Fabric Real-Time Intelligence (ingested from support ticket systems, chat logs)

---

### Recommendation

AI-generated suggestion for adoption or upsell.

**Attributes**:
- `recommendation_id` (string, PK): Unique recommendation identifier (UUID format)
- `customer_id` (string, FK → Customer.account_id, required): Target customer
- `recommendation_type` (enum, required): Type (Adoption, Upsell)
- `text_description` (string, required): Human-readable recommendation text (passed through Content Safety)
- `reasoning_chain` (JSON, required): Structured agent reasoning (see AgentContribution)
- `confidence_score` (float, required): AI confidence (0.0 to 1.0)
- `data_sources` (array[object], required): References to Fabric IQ, Foundry IQ sources used
- `generation_timestamp` (datetime, system): When recommendation was generated
- `outcome_status` (enum, required): Status (Pending, Delivered, Accepted, Declined)
- `delivered_by_agent_id` (string, optional): Support agent who delivered to customer
- `outcome_timestamp` (datetime, optional): When outcome was recorded
- `created_at` (datetime, system): Record creation timestamp
- `updated_at` (datetime, system): Last modification timestamp

**Validation Rules**:
- `customer_id` must reference valid Customer
- `recommendation_type` must match enum values
- `text_description` maximum 1000 characters
- `confidence_score` must be between 0.0 and 1.0
- `outcome_status` must match enum values
- `reasoning_chain` must be valid JSON with required fields

**Relationships**:
- Many-to-One with Customer (many recommendations for one customer)
- One-to-Many with AgentContribution (one recommendation has contributions from multiple agents)

**State Transitions**:
- Pending → Delivered (agent shows to customer)
- Delivered → Accepted (customer agrees to recommendation)
- Delivered → Declined (customer rejects recommendation)
- Declined → Excluded (system stops suggesting this recommendation)

---

### AgentContribution

Record of each AI agent's role in recommendation generation.

**Attributes**:
- `contribution_id` (string, PK): Unique contribution identifier (UUID format)
- `recommendation_id` (string, FK → Recommendation.recommendation_id, required): Associated recommendation
- `agent_type` (enum, required): Agent role (Retrieval, Sentiment, Reasoning, Validation)
- `input_data` (JSON, required): Data provided to agent
- `output_result` (JSON, required): Agent's output
- `confidence_score` (float, required): Agent's confidence (0.0 to 1.0)
- `execution_time_ms` (integer, required): Agent execution duration in milliseconds
- `created_at` (datetime, system): Record creation timestamp

**Validation Rules**:
- `recommendation_id` must reference valid Recommendation
- `agent_type` must match enum values
- `confidence_score` must be between 0.0 and 1.0
- `execution_time_ms` must be positive integer

**Relationships**:
- Many-to-One with Recommendation (many contributions belong to one recommendation)

**Purpose**: Enables explainability (FR-016) and agent orchestration debugging

---

## Relationships Diagram

```
Customer (1) ─────< UsageData (N)
    │
    │
    ├─────< InteractionEvent (N)
    │
    │
    └─────< Recommendation (N)
                │
                └─────< AgentContribution (N)
```

---

## Validation Summary

**Cross-Entity Rules**:
1. Recommendation.customer_id must reference active Customer (not deleted)
2. UsageData.customer_id must reference active Customer
3. InteractionEvent.customer_id must reference active Customer
4. AgentContribution.recommendation_id must reference valid Recommendation
5. Recommendation cannot be generated if Customer has no UsageData (edge case: generate baseline recommendations per edge case rule)
6. Duplicate recommendations prevented: check Recommendation history before generation (FR-014)

**Performance Considerations**:
- Customer, Recommendation, InteractionEvent: Cosmos DB (low-latency access)
- UsageData: Queried via Fabric IQ semantic layer (not stored in Cosmos DB)
- AgentContribution: Stored with Recommendation document (embedded in JSON for single-read performance)

**Data Retention**:
- InteractionEvent: 12 months (per FR-013)
- Recommendation: Indefinite (for analytics and compliance)
- UsageData: Managed by Fabric IQ (90 days per FR-002)
