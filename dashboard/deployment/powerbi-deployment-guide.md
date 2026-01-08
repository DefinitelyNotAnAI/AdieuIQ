# Power BI Service Deployment Guide

**Reports**: adoption-metrics.pbix, upsell-pipeline.pbix  
**Target Environment**: Power BI Service (Production)  
**Workspace**: AdieuIQ-Production  
**Prerequisites**: Fabric Real-Time Intelligence configured, Azure AD groups created

## Prerequisites

### 1. Azure Resources

- [x] Fabric workspace created: `#{FABRIC_WORKSPACE_ID}#`
- [x] Fabric Real-Time Intelligence enabled on workspace
- [x] KQL database created: `adieuiq-rtdb`
- [x] Eventstream configured for data ingestion
- [x] OneLake storage provisioned
- [x] Managed Identity created with Fabric Contributor role

### 2. Azure AD Configuration

- [x] Azure AD groups created:
  - `AdieuIQ-CustomerSuccessManagers@contoso.com`
  - `AdieuIQ-Administrators@contoso.com`
  - `AdieuIQ-SupportAgents@contoso.com`
- [x] Group membership synced from HR system (or manually assigned)
- [x] Test users added to groups for validation

### 3. Power BI Service Configuration

- [x] Power BI Pro licenses assigned to users
- [x] Power BI workspace created: `AdieuIQ-Production`
- [x] Admin Portal settings:
  - Audit logging enabled
  - External sharing disabled (security requirement)
  - Embed code generation disabled (until P3 embedding phase)
- [x] Workspace access granted:
  - IT Admin: Workspace Admin role
  - Data Engineers: Contributor role (for future updates)

### 4. Local Environment (Developer Workstation)

- [x] Power BI Desktop installed (latest version): https://aka.ms/pbidesktopstore
- [x] Azure CLI installed: `winget install Microsoft.AzureCLI`
- [x] Azure AD account with:
  - Power BI Service access
  - Fabric workspace Contributor role
  - Permission to manage RLS roles

### 5. Data Verification

- [x] Fabric Real-Time Intelligence contains sample data:
  - `customers` table (at least 10 rows)
  - `usage_data` table (at least 100 rows)
  - `interaction_events` table (at least 50 rows)
  - `recommendations` table (at least 20 rows)
- [x] Verify data refresh lag: <10 seconds (per FR-012)
- [x] Verify `account_manager_email` column populated in `customers` table

## Step-by-Step Deployment

### Phase 1: Create Power BI Reports (.pbix files)

**Note**: Since .pbix files are binary, this guide assumes you'll create them manually in Power BI Desktop using the design specifications.

#### 1.1: Create adoption-metrics.pbix

1. Open Power BI Desktop
2. Click **Get Data** → **More** → **Azure** → **Azure Data Explorer (Kusto)**
3. Enter connection details:
   - **Cluster**: `https://#{FABRIC_WORKSPACE_ID}#.rtdb.fabric.microsoft.com`
   - **Database**: `adieuiq-rtdb`
   - **Table**: Select all 4 tables (customers, usage_data, interaction_events, recommendations)
4. Click **OK** → Select **DirectQuery** mode (not Import)
5. Click **Load**

6. Create relationships in Model view:
   - `customer_profiles[customer_id]` (1) → (*) `customer_usage_metrics[customer_id]`
   - `customer_profiles[customer_id]` (1) → (*) `customer_interactions[customer_id]`
   - `customer_profiles[customer_id]` (1) → (*) `customer_recommendations[customer_id]`
   - All relationships: Single direction (from dimension to fact)

7. Create DAX measures (copy from [adoption-metrics-design.md](../reports/adoption-metrics-design.md)):
   - Adoption Rate %
   - Low Adoption Count
   - Days Since Last Use
   - Avg Intensity
   - Customer Segment
   - Critical Alerts

8. Create report pages following [adoption-metrics-design.md](../reports/adoption-metrics-design.md):
   - Page 1: Executive Summary (4 visuals)
   - Page 2: Feature-Level Analysis (4 visuals)
   - Page 3: Customer Detail (6 visuals, drill-through)

9. Configure drill-through:
   - Select Page 3 → Drag `customer_id` to **Drill-through** well
   - Enable **Keep all filters** option

10. Save file: `C:\Repos\AdieuIQ\dashboard\reports\adoption-metrics.pbix`

#### 1.2: Create upsell-pipeline.pbix

1. Open Power BI Desktop (new instance)
2. Repeat steps 1.1.2-1.1.5 above (same data source)
3. Add `agent_contribution` table:
   - Click **Get Data** → Select `agent_contribution` table → Load
4. Create relationships in Model view:
   - Same as adoption-metrics.pbix
   - Add: `customer_recommendations[recommendation_id]` (1) → (*) `agent_contribution[recommendation_id]`

5. Create DAX measures (copy from [upsell-pipeline-design.md](../reports/upsell-pipeline-design.md)):
   - Upsell Opportunities
   - Total Revenue Impact
   - Avg Confidence
   - Acceptance Rate %
   - Days to Acceptance
   - High Priority Count
   - Agent Error Rate %

6. Create report pages following [upsell-pipeline-design.md](../reports/upsell-pipeline-design.md):
   - Page 1: Upsell Opportunity Overview (4 visuals)
   - Page 2: Recommendation Pipeline Funnel (5 visuals)
   - Page 3: Customer Opportunity Detail (7 visuals, drill-through)
   - Page 4: Agent Performance Analytics (5 visuals)

7. Configure drill-through:
   - Select Page 3 → Drag `customer_id` to **Drill-through** well

8. Add action buttons on Page 3:
   - Insert **Button** → Set action type: **Web URL**
   - URL: `https://#{BACKEND_API_URL}#/api/recommendations/{recommendation_id}/outcome` (requires Power BI embedded for dynamic URLs; skip for MVP)
   - Note: Button actions require Power BI Embedded; for MVP, users update via frontend application

9. Save file: `C:\Repos\AdieuIQ\dashboard\reports\upsell-pipeline.pbix`

### Phase 2: Configure Row-Level Security

#### 2.1: adoption-metrics.pbix RLS

1. Open `adoption-metrics.pbix` in Power BI Desktop
2. Go to **Modeling** tab → **Manage Roles**
3. Create role: `CustomerSuccessManager`
   - Select `customer_profiles` table
   - Add filter: `[account_manager_email] = USERPRINCIPALNAME()`
4. Create role: `Administrator`
   - Select `customer_profiles` table
   - Add filter: `1 = 1`
5. Create role: `SupportAgent`
   - Select `customer_profiles` table
   - Add filter: `1 = 0`
6. Click **Save** → Save .pbix file

7. Test RLS:
   - Go to **Modeling** tab → **View as**
   - Check **CustomerSuccessManager** role
   - Enter test email: `alice.smith@contoso.com` (Other User)
   - Click **OK**
   - Verify: Only Alice's customers visible in all visuals
   - Click **Stop Viewing** to exit test mode

#### 2.2: upsell-pipeline.pbix RLS

1. Open `upsell-pipeline.pbix` in Power BI Desktop
2. Repeat steps 2.1.2-2.1.7 above (identical configuration)

### Phase 3: Publish Reports to Power BI Service

#### 3.1: Publish adoption-metrics.pbix

1. Open `adoption-metrics.pbix` in Power BI Desktop
2. Click **Publish** (Home tab)
3. Sign in with Azure AD account (if prompted)
4. Select destination workspace: `AdieuIQ-Production`
5. Click **Select**
6. Wait for upload completion (progress bar)
7. Click **Open 'adoption-metrics' in Power BI**
8. Verify report loads correctly in browser (may show all data before RLS assigned)

#### 3.2: Publish upsell-pipeline.pbix

1. Open `upsell-pipeline.pbix` in Power BI Desktop
2. Repeat steps 3.1.2-3.1.8 above

### Phase 4: Assign Azure AD Groups to Roles

#### 4.1: adoption-metrics RLS Assignment

1. Navigate to Power BI Service: https://app.powerbi.com
2. Go to workspace: `AdieuIQ-Production`
3. Locate `adoption-metrics` report → Click **...** (ellipsis) → **Security**
4. Select **CustomerSuccessManager** role:
   - Click **Add user or group**
   - Enter: `AdieuIQ-CustomerSuccessManagers@contoso.com`
   - Verify group found (autocomplete should show group)
   - Click **Add**
5. Select **Administrator** role:
   - Click **Add user or group**
   - Enter: `AdieuIQ-Administrators@contoso.com`
   - Click **Add**
6. Select **SupportAgent** role:
   - Click **Add user or group**
   - Enter: `AdieuIQ-SupportAgents@contoso.com`
   - Click **Add**
7. Click **Save**
8. Wait 5 minutes for role assignments to propagate

#### 4.2: upsell-pipeline RLS Assignment

1. Repeat steps 4.1.1-4.1.8 for `upsell-pipeline` report

### Phase 5: Configure Workspace Settings

#### 5.1: Workspace Access Control

1. In Power BI Service, go to workspace: `AdieuIQ-Production`
2. Click **Access** (right panel)
3. Verify members:
   - IT Admin: **Admin** role (already configured)
   - Data Engineering team: **Contributor** role
   - Add if missing: Click **Add**, enter email, select role
4. Click **Save**

#### 5.2: Workspace Settings

1. In workspace, click **Settings** (gear icon)
2. Go to **Premium** tab:
   - Verify workspace is assigned to Premium capacity (or Fabric capacity)
   - If not assigned, contact Power BI admin
3. Go to **Contact list** tab:
   - Add IT Admin email: `#{ADMIN_EMAIL}#`
   - Add Data Engineering lead: `#{DATA_ENGINEER_EMAIL}#`
4. Click **Save**

### Phase 6: Validation Testing

#### 6.1: Test as Customer Success Manager

1. Open incognito browser window
2. Navigate to: https://app.powerbi.com
3. Sign in as test user: `alice.smith@contoso.com` (must be in AdieuIQ-CustomerSuccessManagers group)
4. Go to workspace: `AdieuIQ-Production`
5. Open `adoption-metrics` report
6. Verify:
   - Report loads in <3 seconds (per FR-005)
   - Only customers assigned to Alice are visible (check Company Name in visuals)
   - Drill-through to Customer Detail works
   - No error messages displayed
7. Open `upsell-pipeline` report
8. Verify:
   - Only Alice's customers visible in Upsell Opportunity Overview
   - Revenue Impact reflects only Alice's customers
   - Agent Performance Analytics page loads correctly

#### 6.2: Test as Administrator

1. Open incognito browser window
2. Sign in as admin user: `admin@contoso.com` (must be in AdieuIQ-Administrators group)
3. Open both reports
4. Verify: All customers visible (no RLS filtering)

#### 6.3: Test as Support Agent

1. Open incognito browser window
2. Sign in as support agent: `support@contoso.com` (must be in AdieuIQ-SupportAgents group)
3. Attempt to open `adoption-metrics` report
4. Expected result: Blank report (no data visible) OR access denied message
5. Confirm: Support agents should use frontend application only, not Power BI

#### 6.4: Performance Testing

1. Sign in as Customer Success Manager
2. Open `adoption-metrics` report
3. Use browser DevTools (F12) → Network tab
4. Measure page load time:
   - **Target**: <3 seconds (per FR-005)
   - **Actual**: Record measurement
5. Apply filter: Date Range = Last 30 days
6. Measure filter application time:
   - **Target**: <1 second
   - **Actual**: Record measurement
7. Drill-through to Customer Detail page
8. Measure drill-through load time:
   - **Target**: <2 seconds
   - **Actual**: Record measurement

**If performance target not met**: Check Fabric Real-Time Intelligence query logs, verify indexes on `customer_id` and `account_manager_email` columns.

### Phase 7: Monitoring Setup

#### 7.1: Enable Power BI Audit Logs

1. Navigate to Power BI Admin Portal: https://app.powerbi.com/admin
2. Go to **Audit and usage settings**
3. Verify **Create audit logs** is **Enabled**
4. If disabled, click **Enable** → Save
5. Note: Audit logs export to Azure AD (available in Purview)

#### 7.2: Configure Application Insights Integration

1. Open Azure Portal: https://portal.azure.com
2. Navigate to Application Insights resource: `adieuiq-appinsights`
3. Go to **Logs** → Run query:
   ```kusto
   traces
   | where message contains "PowerBI"
   | project timestamp, message, severityLevel
   | order by timestamp desc
   | take 100
   ```
4. Verify logs appear (may take 5-10 minutes after first user access)

#### 7.3: Set Up Alerts

1. In Power BI Service, open `upsell-pipeline` report
2. Navigate to **Upsell Opportunity Overview** page
3. Click **...** (ellipsis) on "Total Upsell Opportunities" KPI card → **Manage alerts**
4. Create alert:
   - Condition: Above 100
   - Email recipients: Customer Success Manager lead, IT Admin
   - Frequency: Daily
5. Click **Save and close**

### Phase 8: Documentation Handoff

#### 8.1: User Training Materials

1. Create user guide: `dashboard/docs/user-guide.md`
   - How to access Power BI workspace
   - How to navigate reports
   - How to interpret visuals (adoption rate, confidence score)
   - How to drill-through to customer details
   - Troubleshooting common issues

2. Schedule training session:
   - Audience: Customer Success Managers
   - Duration: 1 hour
   - Agenda: Demo of both reports, Q&A

#### 8.2: Admin Runbook

1. Document in `dashboard/docs/admin-runbook.md`:
   - How to update RLS roles (add/remove users)
   - How to refresh data source connection (if credentials expire)
   - How to update DAX measures (e.g., change thresholds)
   - How to troubleshoot performance issues
   - Escalation path: Power BI admin → Fabric admin → Azure support

## Rollback Plan

**If deployment fails or critical issues found:**

1. **Unpublish reports**:
   - In Power BI Service, go to workspace
   - Click **...** (ellipsis) next to report → **Delete**
   - Confirm deletion
2. **Restore previous version** (if applicable):
   - Power BI Service keeps version history (Settings → Version history → Restore)
3. **Notify users**:
   - Email Customer Success Managers about temporary downtime
   - Provide ETA for fix/re-deployment

## Post-Deployment Checklist

- [ ] Both reports published to `AdieuIQ-Production` workspace
- [ ] RLS roles configured correctly (3 roles per report)
- [ ] Azure AD groups assigned to roles (3 groups per report)
- [ ] Test users verified (Customer Success Manager, Administrator, Support Agent)
- [ ] Performance testing passed (<3s page load, <1s filter, <2s drill-through)
- [ ] Audit logging enabled in Power BI Admin Portal
- [ ] Application Insights logs verified
- [ ] Alert configured for "Total Upsell Opportunities > 100"
- [ ] User training scheduled
- [ ] Admin runbook documented
- [ ] Deployment notes added to `tasks.md` (T051 marked complete)

## Troubleshooting

### Issue: "Couldn't load the model" error in Power BI Service

**Cause**: Fabric Real-Time Intelligence connection timeout  
**Resolution**:
1. Verify Fabric workspace is running (not paused)
2. Check Managed Identity has Fabric Contributor role
3. Test connection in Power BI Desktop → Transform Data → Refresh Preview

### Issue: Blank report after applying RLS

**Cause**: No customers assigned to logged-in user  
**Resolution**:
1. Query Fabric Real-Time Intelligence:
   ```kql
   customers
   | where account_manager_email == "user@contoso.com"
   | count
   ```
2. If count = 0, assign customers to user in data source

### Issue: Slow report performance (>10s page load)

**Cause**: Missing indexes on join columns  
**Resolution**:
1. Check Fabric Real-Time Intelligence indexes:
   ```kql
   .show table customers policy partitioning
   .show table usage_data policy partitioning
   ```
2. Add indexes if missing (coordinate with Data Engineering team)

### Issue: Users cannot access workspace

**Cause**: Insufficient Power BI license  
**Resolution**:
1. Verify user has Power BI Pro license (Azure AD → Licenses)
2. Assign license if missing (may take 15 minutes to propagate)

## Next Steps (Future Phases)

**Phase 5 (P3+): Power BI Embedded Integration**
- Embed reports directly in frontend application
- Implement programmatic filtering (user context from JWT token)
- Add custom navigation (breadcrumbs, back buttons)
- Enable single sign-on (SSO) via MSAL token passthrough

**Phase 6 (P4+): Advanced Analytics**
- Add predictive models (e.g., churn risk score)
- Integrate Azure Machine Learning insights
- Enable what-if analysis (e.g., revenue impact simulator)
