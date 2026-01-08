# Power BI Row-Level Security Configuration

**Objective**: Restrict Customer Success Managers to view only their assigned customers  
**Constitutional Requirement**: Principle III (Security First - Zero Trust)  
**Related Requirement**: FR-009 (RBAC with role-based filtering)

## Security Model

### Azure AD Groups

**Group Name**: AdieuIQ-CustomerSuccessManagers  
**Group Type**: Security Group  
**Membership Source**: Azure AD (synced from HR system)  
**Purpose**: Assign Customer Success Manager role in Power BI

**Group Name**: AdieuIQ-Administrators  
**Group Type**: Security Group  
**Membership Source**: Azure AD (manual assignment)  
**Purpose**: Full access to all customer data for admin tasks

**Group Name**: AdieuIQ-SupportAgents  
**Group Type**: Security Group  
**Membership Source**: Azure AD (synced from HR system)  
**Purpose**: No access to Power BI dashboards (use frontend application only)

### Power BI Roles

#### Role 1: CustomerSuccessManager

**DAX Filter Expression** (applied to `customer_profiles` table):
```dax
[account_manager_email] = USERPRINCIPALNAME()
```

**How It Works**:
1. `USERPRINCIPALNAME()` returns the logged-in user's email (e.g., `john.doe@contoso.com`)
2. Filter compares with `account_manager_email` column in `customer_profiles` table
3. User only sees rows where `account_manager_email` matches their email
4. Filter propagates to related tables via relationships:
   - `customer_recommendations` (via customer_id relationship)
   - `customer_usage_metrics` (via customer_id relationship)
   - `customer_interactions` (via customer_id relationship)

**Example**:
- User: `alice.smith@contoso.com`
- `customer_profiles` rows visible:
  - Customer A (account_manager_email = `alice.smith@contoso.com`) ✓
  - Customer B (account_manager_email = `bob.jones@contoso.com`) ✗
  - Customer C (account_manager_email = `alice.smith@contoso.com`) ✓

**Azure AD Group Assignment**: AdieuIQ-CustomerSuccessManagers

#### Role 2: Administrator

**DAX Filter Expression** (applied to `customer_profiles` table):
```dax
1 = 1
```

**How It Works**:
- Expression always evaluates to TRUE
- No filtering applied; user sees all rows in all tables
- Used for IT admins, executive leadership, data analysts

**Azure AD Group Assignment**: AdieuIQ-Administrators

#### Role 3: SupportAgent (Block Access)

**DAX Filter Expression** (applied to `customer_profiles` table):
```dax
1 = 0
```

**How It Works**:
- Expression always evaluates to FALSE
- No rows visible; effectively blocks access to Power BI
- Support Agents use frontend application only (no dashboard access)

**Azure AD Group Assignment**: AdieuIQ-SupportAgents

## Configuration Steps

### Step 1: Create Roles in Power BI Desktop

1. Open `adoption-metrics.pbix` in Power BI Desktop
2. Navigate to **Modeling** tab → **Manage Roles**
3. Click **Create** → Name: `CustomerSuccessManager`
4. Select `customer_profiles` table → Add filter:
   ```dax
   [account_manager_email] = USERPRINCIPALNAME()
   ```
5. Click **Save**
6. Repeat for `Administrator` role (filter: `1 = 1`) and `SupportAgent` role (filter: `1 = 0`)
7. Save the .pbix file

8. Open `upsell-pipeline.pbix` in Power BI Desktop
9. Repeat steps 2-7 (identical role configuration)

### Step 2: Test Roles in Power BI Desktop

1. Go to **Modeling** tab → **View as**
2. Check **CustomerSuccessManager** role
3. Enter test email: `alice.smith@contoso.com` (Other User)
4. Click **OK**
5. Verify:
   - Only customers with `account_manager_email = alice.smith@contoso.com` are visible
   - KPI cards reflect filtered data
   - Drill-through pages show only filtered customers
6. Exit test mode: **Stop Viewing**

### Step 3: Publish Reports to Power BI Service

1. In Power BI Desktop, click **Publish** (Home tab)
2. Select destination workspace: `AdieuIQ-Production`
3. Wait for upload completion
4. Click **Open [report-name] in Power BI**
5. Repeat for both reports:
   - `adoption-metrics.pbix`
   - `upsell-pipeline.pbix`

### Step 4: Assign Azure AD Groups to Roles (Power BI Service)

**For adoption-metrics report:**
1. Navigate to Power BI Service: https://app.powerbi.com
2. Go to workspace: `AdieuIQ-Production`
3. Click **...** (ellipsis) next to `adoption-metrics` → **Security**
4. Select **CustomerSuccessManager** role:
   - Click **Add user or group**
   - Enter: `AdieuIQ-CustomerSuccessManagers@contoso.com` (Azure AD group)
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

**For upsell-pipeline report:**
- Repeat steps 1-7 above (identical group assignments)

### Step 5: Verify RLS in Power BI Service

1. Log in to Power BI Service as test user (e.g., `alice.smith@contoso.com`)
2. Navigate to `AdieuIQ-Production` workspace
3. Open `adoption-metrics` report
4. Verify:
   - Executive Summary page shows only Alice's customers
   - Top 10 Upsell Opportunities table shows only Alice's customers
   - Drill-through to Customer Detail works correctly
5. Open `upsell-pipeline` report
6. Verify:
   - Upsell Opportunity Overview shows only Alice's customers
   - Revenue Impact reflects only Alice's customers
7. Log out and test with admin user (should see all customers)
8. Test with support agent user (should receive "Access Denied" error or blank report)

## Data Model Relationships (RLS Propagation)

```
customer_profiles [RLS APPLIED HERE]
    ↓ (1:* relationship)
    ├── customer_recommendations [FILTERED via relationship]
    ├── customer_usage_metrics [FILTERED via relationship]
    └── customer_interactions [FILTERED via relationship]
```

**Key Points**:
- RLS filter applied **only** to `customer_profiles` table
- Filters automatically propagate to fact tables via relationships
- Bi-directional filtering **not required** (single direction: dimension → fact)
- Date table **not filtered** (allows time-based analysis across all data)

## Performance Considerations

**Query Performance**:
- RLS adds WHERE clause to every query: `WHERE account_manager_email = 'user@contoso.com'`
- Impact: Minimal (<50ms overhead per query) due to indexed column
- Direct Query mode ensures no data caching across users

**Scalability**:
- Supports up to 500 Customer Success Managers (per Power BI Pro licensing)
- Each user queries only their subset of data (reduces load)
- Fabric Real-Time Intelligence handles concurrent queries efficiently

**Index Requirements**:
- `customer_profiles.account_manager_email`: Indexed (per fabric-connection.json)
- `customer_profiles.customer_id`: Indexed (for relationship joins)
- `customer_recommendations.customer_id`: Indexed (for relationship joins)

## Security Audit & Compliance

**Audit Logging**:
- Power BI Service logs all dashboard access (user, timestamp, report name)
- Logs exported to Log Analytics workspace for Purview integration
- Constitutional Principle IV: Observability First

**Purview Integration**:
- Power BI reports auto-cataloged as sensitive data assets
- Data lineage tracked: Fabric Real-Time Intelligence → Power BI → User
- Sensitivity labels applied: "Confidential - Internal Only"

**Compliance Validation**:
- [ ] RLS prevents cross-customer data leakage (verified via test users)
- [ ] Azure AD group membership synced from authoritative source (HR system)
- [ ] Audit logs enabled in Power BI Service (Admin Portal → Audit logs → On)
- [ ] Purview data map reflects Power BI reports (auto-scanned weekly)
- [ ] Sensitivity labels applied to reports (Manual step: Info Protection → Confidential)

## Troubleshooting

### Issue: User sees all customers instead of only assigned ones

**Cause**: User is member of Administrator role  
**Resolution**: Remove user from `AdieuIQ-Administrators` Azure AD group (unless admin access intended)

### Issue: User sees no data (blank report)

**Cause 1**: User has no customers assigned in `customer_profiles.account_manager_email`  
**Resolution**: Update customer assignments in data source (OneLake)

**Cause 2**: User is member of SupportAgent role  
**Resolution**: Remove user from `AdieuIQ-SupportAgents` group; add to `AdieuIQ-CustomerSuccessManagers`

**Cause 3**: Email mismatch (user logs in with different email than stored in data)  
**Resolution**: Ensure `account_manager_email` uses same format as Azure AD UPN (e.g., `user@contoso.com`, not `user@contoso.onmicrosoft.com`)

### Issue: RLS not applied after publishing

**Cause**: Role assignment missing in Power BI Service  
**Resolution**: Follow Step 4 above to assign Azure AD groups to roles

### Issue: Performance degradation with RLS

**Cause**: Missing index on `account_manager_email` column  
**Resolution**: Verify index exists in Fabric Real-Time Intelligence KQL table:
```kql
.show table customers policy partitioning
```

## Maintenance Notes

**Ownership**: IT Security team (primary), Power BI Admin (backup)  
**Review Frequency**: Quarterly review of Azure AD group memberships  
**Change Management**: All role changes require approval via ServiceNow ticket  
**Documentation**: Update this file if RLS logic changes (e.g., adding region-based filtering)

## Future Enhancements (Post-MVP)

1. **Dynamic RLS**: Filter by region, product line (multi-dimensional security)
2. **Object-Level Security**: Hide specific report pages based on role (e.g., Agent Performance page for admins only)
3. **Column-Level Security**: Hide `estimated_revenue_impact` column from junior Customer Success Managers
4. **Embedding RLS**: Apply same security model when embedding reports in frontend application (Power BI Embedded SDK)
