# Power BI Report: Upsell Pipeline Dashboard

**Report Name**: upsell-pipeline.pbix  
**Target Audience**: Customer Success Managers  
**Data Source**: Fabric Real-Time Intelligence (Direct Query)  
**Refresh Mode**: Direct Query (<10s lag per FR-012)  
**Row-Level Security**: Enabled (Azure AD groups)

## Report Pages

### Page 1: Upsell Opportunity Overview

**Purpose**: Prioritized list of upsell-ready customers with revenue impact

**Visuals**:
1. **KPI Cards** (top row):
   - Total Upsell Opportunities (count)
   - Total Estimated Revenue Impact ($)
   - Average Confidence Score (%)
   - Accepted Recommendations (conversion rate %)

2. **Upsell Priority Matrix** (scatter chart):
   - X-axis: Confidence Score (0-100%)
   - Y-axis: Estimated Revenue Impact ($)
   - Size: Days since last interaction
   - Color: Sentiment Score (Red <0, Yellow 0-0.5, Green >0.5)
   - Tooltip: Company Name, Recommended Products
   - Quadrants:
     - Top-Right: "High Priority" (High confidence + High revenue)
     - Top-Left: "Nurture" (Low confidence + High revenue)
     - Bottom-Right: "Quick Wins" (High confidence + Low revenue)
     - Bottom-Left: "Low Priority"

3. **Revenue Impact by Product Tier** (clustered bar chart):
   - Y-axis: Product Tier (Basic, Professional, Enterprise)
   - X-axis: Total Estimated Revenue Impact ($)
   - Legend: Recommendation Type (Adoption vs Upsell)
   - Sort: Descending by revenue

4. **Top 10 Upsell Opportunities** (table):
   - Columns: Rank, Company Name, Current Tier, Recommended Products, Confidence %, Revenue Impact ($), Reasoning (truncated), Account Manager
   - Sort: Revenue Impact (descending)
   - Conditional formatting: Confidence % (green >70%, yellow 50-70%, red <50%)
   - Action: Click to drill-through to Opportunity Detail

### Page 2: Recommendation Pipeline Funnel

**Purpose**: Track recommendation lifecycle from generation to acceptance

**Filters** (left sidebar):
- Date Range (last 7/30/90/365 days)
- Recommendation Type (Adoption, Upsell)
- Product Tier (multi-select)
- Account Manager (multi-select)

**Visuals**:
1. **Conversion Funnel** (funnel chart):
   - Stages: Generated → Delivered → Accepted / Declined
   - Values: Recommendation count
   - Conversion rates: % between stages
   - Tooltip: Average days in stage

2. **Time to Acceptance** (histogram):
   - X-axis: Days from Generated to Accepted (bins: 0-7, 8-14, 15-30, 31-60, 60+)
   - Y-axis: Recommendation count
   - Color: Recommendation Type
   - Purpose: Identify sales cycle duration

3. **Outcome Status by Recommendation Type** (100% stacked bar chart):
   - Y-axis: Recommendation Type (Adoption, Upsell)
   - X-axis: Percentage
   - Legend: Outcome Status (Accepted, Declined, Pending)
   - Color: Green (Accepted), Red (Declined), Yellow (Pending)

4. **Revenue Realization** (waterfall chart):
   - X-axis: Month
   - Y-axis: Cumulative Revenue Impact ($)
   - Bars: Accepted recommendations (green), Declined (red)
   - Connector: Running total
   - Goal line: Annual revenue target (configurable)

5. **Recommendation Quality Metrics** (card visuals):
   - Average Confidence Score (%)
   - Acceptance Rate for High Confidence (>70%)
   - Acceptance Rate for Low Confidence (<50%)
   - Purpose: Validate agent orchestration quality

### Page 3: Customer Opportunity Detail (Drill-Through)

**Purpose**: Deep dive into individual customer upsell opportunity

**Drill-Through Filters**:
- Customer ID (from Upsell Opportunity Overview)

**Visuals**:
1. **Customer Header** (card visuals):
   - Company Name
   - Current Product Tier
   - Industry Segment
   - Account Manager Email
   - Last Interaction Date

2. **Recommended Products** (table):
   - Columns: Product Name, Current Status (Owned/Not Owned), Pricing ($), Estimated Value ($), Confidence (%)
   - Conditional formatting: Highlight products customer doesn't own
   - Action: "Mark as Delivered" button (updates recommendation status)

3. **AI Reasoning** (card visual):
   - Text: Full reasoning text from ReasoningAgent
   - Format: Markdown-style formatting (bullet points, bold key phrases)
   - Purpose: Provides explainability per FR-016

4. **Agent Contribution Breakdown** (donut chart):
   - Segments: RetrievalAgent, SentimentAgent, ReasoningAgent, ValidationAgent
   - Values: Contribution score (from agent_contribution.contribution_score)
   - Tooltip: Key factors from each agent

5. **Historical Recommendations** (timeline):
   - X-axis: Date (generated_at)
   - Y-axis: Confidence Score (%)
   - Markers: Recommendation type (icon)
   - Color: Outcome status (Accepted/Green, Declined/Red, Pending/Yellow)
   - Tooltip: Recommended products, reasoning (truncated)

6. **Customer Health Indicators** (gauge charts):
   - **Adoption Rate**: Current % of features used (target: >70%)
   - **Sentiment Score**: Average sentiment (target: >0.5)
   - **Interaction Frequency**: Interactions per month (target: <2 support tickets)

7. **Action Buttons** (buttons):
   - "Mark as Delivered" → Updates recommendation.outcome_status to 'Delivered'
   - "Mark as Accepted" → Updates to 'Accepted', logs agent_confirmed timestamp
   - "Mark as Declined" → Updates to 'Declined'
   - "View Adoption Dashboard" → Navigates to adoption-metrics.pbix Customer Detail page

### Page 4: Agent Performance Analytics

**Purpose**: Monitor AI agent orchestration quality and trends

**Filters** (left sidebar):
- Agent Type (Retrieval, Sentiment, Reasoning, Validation)
- Date Range (last 30/90/365 days)

**Visuals**:
1. **Agent Execution Timeline** (line chart):
   - X-axis: Date (daily aggregation)
   - Y-axis: Average execution time (ms)
   - Legend: Agent Type
   - Goal line: 2000ms (FR-005 target)
   - Purpose: Identify performance regressions

2. **Validation Agent Block Reasons** (treemap):
   - Hierarchy: Block Reason (Duplicate, Content Safety, Low Confidence)
   - Size: Count of blocked recommendations
   - Color: Block reason type
   - Tooltip: Percentage of total blocks

3. **Confidence Score Distribution** (histogram):
   - X-axis: Confidence Score bins (0-20%, 21-40%, 41-60%, 61-80%, 81-100%)
   - Y-axis: Recommendation count
   - Color: Outcome Status (Accepted/Green, Declined/Red)
   - Purpose: Validate confidence calibration

4. **Agent Contribution Heatmap** (matrix):
   - Rows: Agent Type
   - Columns: Recommendation Type (Adoption, Upsell)
   - Values: Average contribution score
   - Color Scale: Blue (high) → White → Red (low)

5. **Error Rate by Agent** (clustered column chart):
   - X-axis: Agent Type
   - Y-axis: Error rate (%)
   - Legend: Error type (Timeout, API failure, Validation failure)
   - Target line: <1% (constitutional requirement for graceful degradation)

## DAX Measures

### Total Upsell Opportunities

```dax
Upsell Opportunities = 
CALCULATE(
    DISTINCTCOUNT(customer_recommendations[recommendation_id]),
    customer_recommendations[recommendation_type] = "Upsell",
    customer_recommendations[outcome_status] IN {"Pending", "Delivered"}
)
```

### Total Estimated Revenue Impact

```dax
Total Revenue Impact = 
CALCULATE(
    SUM(customer_recommendations[estimated_revenue_impact]),
    customer_recommendations[outcome_status] <> "Declined"
)
```

### Average Confidence Score

```dax
Avg Confidence = 
AVERAGE(customer_recommendations[confidence_score]) * 100
```

### Acceptance Rate

```dax
Acceptance Rate % = 
VAR TotalDelivered = 
    CALCULATE(
        COUNTROWS(customer_recommendations),
        customer_recommendations[outcome_status] IN {"Accepted", "Declined"}
    )
VAR Accepted = 
    CALCULATE(
        COUNTROWS(customer_recommendations),
        customer_recommendations[outcome_status] = "Accepted"
    )
RETURN
DIVIDE(Accepted, TotalDelivered, 0) * 100
```

### Days in Stage (Delivered → Accepted)

```dax
Days to Acceptance = 
DATEDIFF(
    customer_recommendations[delivered_at],
    customer_recommendations[agent_confirmed],
    DAY
)
```

### High Priority Opportunities

```dax
High Priority Count = 
CALCULATE(
    DISTINCTCOUNT(customer_recommendations[recommendation_id]),
    customer_recommendations[confidence_score] >= 0.7,
    customer_recommendations[estimated_revenue_impact] >= 10000
)
```

### Acceptance Rate for High Confidence

```dax
High Confidence Acceptance % = 
VAR HighConfidence = 
    CALCULATE(
        COUNTROWS(customer_recommendations),
        customer_recommendations[confidence_score] >= 0.7,
        customer_recommendations[outcome_status] IN {"Accepted", "Declined"}
    )
VAR HighConfAccepted = 
    CALCULATE(
        COUNTROWS(customer_recommendations),
        customer_recommendations[confidence_score] >= 0.7,
        customer_recommendations[outcome_status] = "Accepted"
    )
RETURN
DIVIDE(HighConfAccepted, HighConfidence, 0) * 100
```

### Revenue Realization (Accepted Only)

```dax
Realized Revenue = 
CALCULATE(
    SUM(customer_recommendations[estimated_revenue_impact]),
    customer_recommendations[outcome_status] = "Accepted"
)
```

### Agent Error Rate

```dax
Agent Error Rate % = 
VAR TotalExecutions = COUNTROWS(agent_contribution)
VAR ErrorExecutions = 
    CALCULATE(
        COUNTROWS(agent_contribution),
        agent_contribution[contribution_score] = 0
    )
RETURN
DIVIDE(ErrorExecutions, TotalExecutions, 0) * 100
```

## Data Model Relationships

```
customer_profiles (1) --> (*) customer_recommendations
customer_recommendations (1) --> (*) agent_contribution

Date Table (1) --> (*) customer_recommendations[generated_at]
Date Table (1) --> (*) customer_recommendations[delivered_at]
Date Table (1) --> (*) customer_recommendations[agent_confirmed]
```

**Relationship Type**: One-to-Many (1:*)  
**Cross-filter Direction**: Both (for drill-through scenarios)  
**Cardinality Enforcement**: Referential integrity enabled

## Row-Level Security (RLS)

**Role**: CustomerSuccessManager

**DAX Filter** (applied to customer_profiles table):
```dax
[account_manager_email] = USERPRINCIPALNAME()
```

**Effect**: Customer Success Managers only see upsell opportunities for their assigned customers.

**Role Assignment**:
- Azure AD Group: "AdieuIQ-CustomerSuccessManagers"
- Members: Auto-populated via HR sync

## Deployment Configuration

**Power BI Workspace**: AdieuIQ-Production  
**Refresh Schedule**: N/A (Direct Query mode)  
**Gateway**: Not required (Fabric native integration)  
**Licensing**: Power BI Pro (sufficient for <500 users)

**Parameters** (to be configured during deployment):
- `FabricWorkspaceId`: #{FABRIC_WORKSPACE_ID}#
- `KQLDatabaseName`: adieuiq-rtdb
- `TenantId`: #{AZURE_TENANT_ID}#

## Performance Optimization

1. **Lazy Loading**: Customer Opportunity Detail page loads data only on drill-through
2. **Top N Filtering**: Top 10 Upsell Opportunities table limits to 10 rows
3. **Date Filtering**: Default to last 30 days; user can expand to 365 days
4. **Aggregations**: Use SUM/AVG instead of row-level calculations where possible
5. **Visual Interaction**: Disable cross-filtering between Priority Matrix and Revenue Impact chart

**Expected Query Performance**:
- Initial page load: <3 seconds (per FR-005)
- Filter application: <1 second
- Drill-through: <2 seconds
- Button actions (Mark as Delivered): <500ms

## Power BI Embedded Integration (Future)

**Phase 4 (P2)**: Basic Power BI Service deployment  
**Future Enhancement (P3+)**: Embed reports directly in frontend application

**Benefits of Embedding**:
- Unified user experience (no separate Power BI Service login)
- Programmatic filtering (e.g., auto-filter to logged-in user's customers)
- Custom navigation (breadcrumbs, back buttons)

**Implementation** (when ready):
- Use Power BI Embedded SDK in frontend/src/services/powerbi-client.ts
- Generate embed tokens via backend API (POST /api/powerbi/embed-token)
- Render reports in frontend/src/components/DashboardEmbed.tsx
- Apply user context via RLS (userprincipalname filter)

## Testing Checklist

- [ ] Verify row-level security: Test with CustomerSuccessManager user account
- [ ] Validate data refresh lag: Confirm <10s between Fabric ingestion and Power BI display (FR-012)
- [ ] Test drill-through: Navigate from Upsell Opportunity Overview → Customer Opportunity Detail
- [ ] Verify conditional formatting: Confidence % displays color-coded (green/yellow/red)
- [ ] Test action buttons: "Mark as Delivered" updates recommendation.outcome_status in Cosmos DB
- [ ] Cross-browser testing: Chrome, Edge, Safari (Power BI Service)
- [ ] Mobile responsiveness: Test on tablet view (iPad Pro)
- [ ] Performance validation: Measure query duration with 10,000+ recommendations
- [ ] Security audit: Confirm no revenue data visible to unauthorized users
- [ ] Agent Performance page: Verify execution time data flows from OpenTelemetry spans

## Maintenance Notes

- **Ownership**: Customer Success team (primary), IT Admin (backup)
- **Update Frequency**: Monthly review of revenue targets and priority thresholds
- **Monitoring**: Application Insights tracks dashboard access (per Principle IV)
- **Compliance**: Purview automatically catalogs report as sensitive financial data asset
- **Alerts**: Configure Power BI alerts for "Total Upsell Opportunities" exceeding 100 (indicates backlog)
