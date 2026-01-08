# Power BI Report: Adoption Metrics Dashboard

**Report Name**: adoption-metrics.pbix  
**Target Audience**: Customer Success Managers  
**Data Source**: Fabric Real-Time Intelligence (Direct Query)  
**Refresh Mode**: Direct Query (<10s lag per FR-012)  
**Row-Level Security**: Enabled (Azure AD groups)

## Report Pages

### Page 1: Executive Summary

**Purpose**: High-level overview of feature adoption across customer base

**Visuals**:
1. **KPI Cards** (top row):
   - Total Active Customers
   - Average Feature Adoption Rate (%)
   - Low-Adoption Customers (count)
   - Critical Alerts (count)

2. **Feature Adoption Trend** (line chart):
   - X-axis: Date (last 90 days)
   - Y-axis: Adoption Rate (%)
   - Legend: Feature Name
   - Tooltip: Customer count, Usage count

3. **Customer Segmentation** (donut chart):
   - Segments: High Adoption (>75%), Medium (50-75%), Low (<50%), Unused
   - Value: Customer count
   - Drill-through: Customer Detail page

4. **Low-Adoption Alerts** (table):
   - Columns: Company Name, Feature Name, Last Used, Days Since Last Use, Account Manager
   - Sort: Days Since Last Use (descending)
   - Conditional formatting: Red for >30 days
   - Action: Drill-through to Customer Detail

### Page 2: Feature-Level Analysis

**Purpose**: Deep dive into individual feature usage patterns

**Filters** (left sidebar):
- Feature Name (multi-select dropdown)
- Product Tier (Basic, Professional, Enterprise)
- Industry Segment (multi-select)
- Date Range (last 7/30/90 days)

**Visuals**:
1. **Feature Usage Heatmap** (matrix):
   - Rows: Feature Name
   - Columns: Product Tier
   - Values: Average Usage Count
   - Color Scale: Green (high) → Yellow → Red (low)

2. **Adoption by Product Tier** (clustered column chart):
   - X-axis: Product Tier
   - Y-axis: Adoption Rate (%)
   - Legend: Intensity Score (High, Medium, Low, Unused)

3. **Usage Trends by Feature** (line chart):
   - X-axis: Date (weekly aggregation)
   - Y-axis: Total Usage Count
   - Legend: Feature Name (top 10 by usage)
   - Tooltip: Customer count, Average intensity

4. **Feature Correlation** (scatter chart):
   - X-axis: Feature A usage count
   - Y-axis: Feature B usage count
   - Size: Customer count
   - Tooltip: Company name, Product tier
   - Purpose: Identify feature bundles for upsell

### Page 3: Customer Detail (Drill-Through)

**Purpose**: Individual customer adoption profile

**Drill-Through Filters**:
- Customer ID (from Executive Summary or Feature-Level pages)

**Visuals**:
1. **Customer Header** (card visuals):
   - Company Name
   - Product Tier
   - Industry Segment
   - Account Manager Email

2. **Feature Adoption Breakdown** (100% stacked bar chart):
   - Y-axis: Feature Name
   - X-axis: Adoption % (High usage, Medium, Low, Unused)
   - Color: Intensity Score

3. **Usage Timeline** (line chart):
   - X-axis: Date (last 90 days)
   - Y-axis: Total Usage Count
   - Legend: Top 5 features by usage

4. **Interaction Sentiment** (gauge chart):
   - Value: Average Sentiment Score (-1 to 1)
   - Target: 0.5 (healthy threshold)
   - Color: Red (<0), Yellow (0-0.5), Green (>0.5)

5. **Recent Interactions** (table):
   - Columns: Date, Event Type, Summary, Sentiment, Resolution Status
   - Sort: Date (descending)
   - Row limit: 10 most recent

6. **Action Items** (card):
   - Display: Recommendation count (pending, delivered, accepted)
   - Button: "View Recommendations" (navigates to Upsell Pipeline report)

## DAX Measures

### Adoption Rate Calculation

```dax
Adoption Rate % = 
VAR TotalFeatures = DISTINCTCOUNT(customer_usage_metrics[feature_name])
VAR UsedFeatures = 
    CALCULATE(
        DISTINCTCOUNT(customer_usage_metrics[feature_name]),
        customer_usage_metrics[intensity_score] <> "Unused"
    )
RETURN
DIVIDE(UsedFeatures, TotalFeatures, 0) * 100
```

### Low-Adoption Customers

```dax
Low Adoption Count = 
CALCULATE(
    DISTINCTCOUNT(customer_usage_metrics[customer_id]),
    [Adoption Rate %] < 50
)
```

### Days Since Last Use

```dax
Days Since Last Use = 
DATEDIFF(
    MAX(customer_usage_metrics[last_used_at]),
    TODAY(),
    DAY
)
```

### Average Intensity Score (Numeric)

```dax
Avg Intensity = 
VAR IntensityMap = 
    SWITCH(
        customer_usage_metrics[intensity_score],
        "High", 3,
        "Medium", 2,
        "Low", 1,
        "Unused", 0
    )
RETURN
AVERAGE(IntensityMap)
```

### Feature Adoption Trend (Time Intelligence)

```dax
Adoption Rate MoM Change = 
VAR CurrentMonthAdoption = [Adoption Rate %]
VAR PreviousMonthAdoption = 
    CALCULATE(
        [Adoption Rate %],
        DATEADD('Date'[Date], -1, MONTH)
    )
RETURN
CurrentMonthAdoption - PreviousMonthAdoption
```

### Customer Segment Classification

```dax
Customer Segment = 
VAR AdoptionRate = [Adoption Rate %]
RETURN
SWITCH(
    TRUE(),
    AdoptionRate >= 75, "High Adoption",
    AdoptionRate >= 50, "Medium Adoption",
    AdoptionRate > 0, "Low Adoption",
    "Unused"
)
```

### Critical Alerts

```dax
Critical Alerts = 
CALCULATE(
    COUNTROWS(customer_usage_metrics),
    customer_usage_metrics[intensity_score] = "Unused",
    [Days Since Last Use] > 30
)
```

## Data Model Relationships

```
customer_profiles (1) --> (*) customer_usage_metrics
customer_profiles (1) --> (*) customer_interactions
customer_profiles (1) --> (*) customer_recommendations

Date Table (1) --> (*) customer_usage_metrics[timestamp]
Date Table (1) --> (*) customer_interactions[occurred_at]
Date Table (1) --> (*) customer_recommendations[generated_at]
```

**Relationship Type**: One-to-Many (1:*)  
**Cross-filter Direction**: Single (from dimension to fact tables)  
**Cardinality Enforcement**: Referential integrity enabled

## Row-Level Security (RLS)

**Role**: CustomerSuccessManager

**DAX Filter** (applied to customer_profiles table):
```dax
[account_manager_email] = USERPRINCIPALNAME()
```

**Effect**: Customer Success Managers only see data for customers assigned to them in the account_manager_email field.

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

1. **Query Reduction**: Use aggregations for trend visuals (weekly/monthly rollups)
2. **Column Indexing**: Indexed columns per fabric-connection.json (customer_id, feature_name, occurred_at, generated_at)
3. **Visual Interaction**: Disable cross-filtering between independent visuals (e.g., KPI cards and trend charts)
4. **Date Filtering**: Default to last 90 days; user can expand to 365 days if needed
5. **Row Limits**: Apply top N filters (e.g., top 100 customers by usage count)

**Expected Query Performance**:
- Initial page load: <3 seconds (per FR-005)
- Filter application: <1 second
- Drill-through: <2 seconds

## Testing Checklist

- [ ] Verify row-level security: Test with CustomerSuccessManager user account
- [ ] Validate data refresh lag: Confirm <10s between Fabric ingestion and Power BI display (FR-012)
- [ ] Test drill-through: Navigate from Executive Summary → Customer Detail
- [ ] Verify conditional formatting: Low-adoption alerts display red for >30 days
- [ ] Cross-browser testing: Chrome, Edge, Safari (Power BI Service)
- [ ] Mobile responsiveness: Test on tablet view (iPad Pro)
- [ ] Performance validation: Measure query duration with 10,000+ customer records
- [ ] Security audit: Confirm no PII visible to unauthorized users

## Maintenance Notes

- **Ownership**: Customer Success team (primary), IT Admin (backup)
- **Update Frequency**: Quarterly review of KPIs and segmentation thresholds
- **Monitoring**: Application Insights tracks dashboard access (per Principle IV)
- **Compliance**: Purview automatically catalogs report as sensitive data asset
