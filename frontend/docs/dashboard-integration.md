# Dashboard Links Integration Guide

**Component**: DashboardLinks  
**Purpose**: Display Power BI dashboard links with role-based access control  
**Location**: `frontend/src/components/DashboardLinks/`

## Overview

The DashboardLinks component provides a user interface for accessing Power BI dashboards (Adoption Metrics and Upsell Pipeline) with automatic role-based filtering. Only users with `CustomerSuccessManager` or `Administrator` roles can see the dashboard links.

## Component API

### Props

```typescript
interface DashboardLinksProps {
  userRoles: string[];           // User's Azure AD roles from JWT token
  powerBiWorkspaceUrl?: string;  // Power BI workspace URL (optional, has default)
}
```

### Default Props

- `powerBiWorkspaceUrl`: `'https://app.powerbi.com/groups/00000000-0000-0000-0000-000000000000'`
  - **IMPORTANT**: Replace with actual workspace ID during deployment

## Integration Steps

### Step 1: Install MSAL React (if not already installed)

```bash
npm install @azure/msal-react @azure/msal-browser
```

### Step 2: Configure MSAL Authentication

**File**: `frontend/src/authConfig.ts`

```typescript
import { Configuration, PopupRequest } from "@azure/msal-browser";

// MSAL configuration
export const msalConfig: Configuration = {
  auth: {
    clientId: process.env.REACT_APP_AZURE_CLIENT_ID || "YOUR-CLIENT-ID",
    authority: `https://login.microsoftonline.com/${process.env.REACT_APP_AZURE_TENANT_ID || "YOUR-TENANT-ID"}`,
    redirectUri: process.env.REACT_APP_REDIRECT_URI || "http://localhost:3000",
  },
  cache: {
    cacheLocation: "sessionStorage",
    storeAuthStateInCookie: false,
  },
};

// Add scopes for API access and roles
export const loginRequest: PopupRequest = {
  scopes: ["User.Read", "api://adieuiq/Customers.Read"],
};
```

### Step 3: Wrap App with MSAL Provider

**File**: `frontend/src/index.tsx`

```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import { PublicClientApplication } from '@azure/msal-browser';
import { MsalProvider } from '@azure/msal-react';
import App from './App';
import { msalConfig } from './authConfig';

const msalInstance = new PublicClientApplication(msalConfig);

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <MsalProvider instance={msalInstance}>
      <App />
    </MsalProvider>
  </React.StrictMode>
);
```

### Step 4: Create Dashboard Page Component

**File**: `frontend/src/pages/DashboardPage.tsx` (already created)

This page extracts user roles from the JWT token and passes them to the DashboardLinks component.

### Step 5: Add Routing (React Router)

**File**: `frontend/src/App.tsx`

```typescript
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { MsalAuthenticationTemplate } from '@azure/msal-react';
import { InteractionType } from '@azure/msal-browser';
import DashboardPage from './pages/DashboardPage';
import CustomerSearchPage from './pages/CustomerSearchPage'; // Example
import { loginRequest } from './authConfig';

function App() {
  return (
    <Router>
      <Routes>
        {/* Protected route: Dashboard */}
        <Route
          path="/dashboards"
          element={
            <MsalAuthenticationTemplate
              interactionType={InteractionType.Redirect}
              authenticationRequest={loginRequest}
            >
              <DashboardPage />
            </MsalAuthenticationTemplate>
          }
        />

        {/* Other routes */}
        <Route path="/customers" element={<CustomerSearchPage />} />
        <Route path="/" element={<Navigate to="/customers" />} />
      </Routes>
    </Router>
  );
}

export default App;
```

### Step 6: Extract User Roles from JWT Token

**File**: `frontend/src/pages/DashboardPage.tsx` (enhanced)

```typescript
import React from 'react';
import { useMsal } from '@azure/msal-react';
import DashboardLinks from '../components/DashboardLinks/DashboardLinks';

const DashboardPage: React.FC = () => {
  const { accounts } = useMsal();
  
  // Get first account (logged-in user)
  const account = accounts[0];
  
  // Extract roles from JWT token claims
  // Roles are configured in Azure AD app registration (App roles)
  const userRoles: string[] = account?.idTokenClaims?.roles || [];
  
  // Get Power BI workspace URL from environment variable
  const powerBiWorkspaceUrl = process.env.REACT_APP_POWERBI_WORKSPACE_URL;

  return (
    <div className="dashboard-page">
      <header className="page-header">
        <h1>Analytics Dashboards</h1>
        <p>Welcome, {account?.name || 'User'}</p>
      </header>
      
      <DashboardLinks 
        userRoles={userRoles}
        powerBiWorkspaceUrl={powerBiWorkspaceUrl}
      />
      
      {userRoles.length === 0 && (
        <div className="no-access-message">
          <p>You do not have access to any dashboards.</p>
          <p>Please contact your administrator to request access.</p>
        </div>
      )}
    </div>
  );
};

export default DashboardPage;
```

### Step 7: Configure Environment Variables

**File**: `frontend/.env`

```bash
# Azure AD Configuration
REACT_APP_AZURE_TENANT_ID=YOUR-TENANT-ID-HERE
REACT_APP_AZURE_CLIENT_ID=YOUR-CLIENT-ID-HERE
REACT_APP_REDIRECT_URI=http://localhost:3000

# Power BI Configuration
REACT_APP_POWERBI_WORKSPACE_URL=https://app.powerbi.com/groups/YOUR-WORKSPACE-ID-HERE

# Backend API
REACT_APP_API_BASE_URL=https://api.adieuiq.com
```

**File**: `frontend/.env.production`

```bash
# Production environment overrides
REACT_APP_REDIRECT_URI=https://adieuiq.com
REACT_APP_POWERBI_WORKSPACE_URL=https://app.powerbi.com/groups/PRODUCTION-WORKSPACE-ID
REACT_APP_API_BASE_URL=https://api.adieuiq.com
```

### Step 8: Configure Azure AD App Roles

**Azure Portal Steps**:
1. Navigate to Azure AD → App registrations → Select app
2. Go to **App roles** → **Create app role**
3. Create role: `CustomerSuccessManager`
   - Display name: Customer Success Manager
   - Allowed member types: Users/Groups
   - Value: `CustomerSuccessManager`
   - Description: Access to customer dashboards and recommendations
4. Create role: `Administrator`
   - Display name: Administrator
   - Allowed member types: Users/Groups
   - Value: `Administrator`
   - Description: Full access to all features
5. Create role: `SupportAgent`
   - Display name: Support Agent
   - Allowed member types: Users/Groups
   - Value: `SupportAgent`
   - Description: Access to customer support features only
6. Click **Save**

### Step 9: Assign Users to Roles

**Azure Portal Steps**:
1. Navigate to Azure AD → Enterprise applications → Select app
2. Go to **Users and groups** → **Add user/group**
3. Select user or Azure AD group
4. Select role (e.g., CustomerSuccessManager)
5. Click **Assign**

**Example Assignments**:
- Alice Smith → CustomerSuccessManager role
- Bob Jones → Administrator role
- Support Team group → SupportAgent role

### Step 10: Add Navigation Link (Optional)

**File**: `frontend/src/components/Navigation/Navigation.tsx`

```typescript
import React from 'react';
import { Link } from 'react-router-dom';
import { useMsal } from '@azure/msal-react';

const Navigation: React.FC = () => {
  const { accounts } = useMsal();
  const account = accounts[0];
  const userRoles: string[] = account?.idTokenClaims?.roles || [];
  
  // Show dashboard link only for authorized roles
  const canAccessDashboards = userRoles.some(role => 
    ['CustomerSuccessManager', 'Administrator'].includes(role)
  );

  return (
    <nav className="navigation">
      <Link to="/customers">Customers</Link>
      {canAccessDashboards && (
        <Link to="/dashboards">Dashboards</Link>
      )}
    </nav>
  );
};

export default Navigation;
```

## Testing

### Test Case 1: Customer Success Manager Access

1. Log in as user with `CustomerSuccessManager` role
2. Navigate to `/dashboards`
3. **Expected Result**:
   - Both dashboard cards visible (Adoption Metrics, Upsell Pipeline)
   - Clicking card opens Power BI Service in new tab
   - Power BI shows only user's assigned customers (RLS applied)

### Test Case 2: Administrator Access

1. Log in as user with `Administrator` role
2. Navigate to `/dashboards`
3. **Expected Result**:
   - Both dashboard cards visible
   - Power BI shows all customers (no RLS filtering)

### Test Case 3: Support Agent Access

1. Log in as user with `SupportAgent` role
2. Navigate to `/dashboards`
3. **Expected Result**:
   - No dashboard cards visible
   - Info message: "You do not have access to any dashboards"

### Test Case 4: No Roles Assigned

1. Log in as user with no roles
2. Navigate to `/dashboards`
3. **Expected Result**:
   - Component renders nothing (returns null)
   - Page shows "no access" message (from DashboardPage parent)

## Troubleshooting

### Issue: Roles not appearing in JWT token

**Cause**: User not assigned to app role in Azure AD  
**Resolution**:
1. Azure AD → Enterprise applications → Select app
2. Users and groups → Verify user is assigned to a role
3. User must log out and log in again to refresh token

### Issue: Dashboard links visible but Power BI shows "Access Denied"

**Cause**: User not added to Power BI RLS role  
**Resolution**:
1. Power BI Service → Workspace → Report → Security
2. Verify user's Azure AD group assigned to RLS role (e.g., `AdieuIQ-CustomerSuccessManagers`)

### Issue: Environment variable not loading

**Cause**: .env file not in root of frontend/ directory  
**Resolution**:
1. Verify .env file location: `frontend/.env`
2. Restart development server: `npm start`
3. Check console: `console.log(process.env.REACT_APP_POWERBI_WORKSPACE_URL)`

## Security Considerations

1. **Never hardcode credentials**: Use environment variables for all sensitive data
2. **Validate roles on backend**: Frontend role check is for UX only; backend must enforce authorization
3. **HTTPS only**: Power BI embeds require HTTPS (even in dev, use `https://localhost:3000`)
4. **Token expiration**: MSAL automatically refreshes tokens; handle refresh failures gracefully
5. **Audit logging**: All dashboard access logged in Power BI Service and Application Insights

## Future Enhancements (Power BI Embedded)

**Phase 5 (P3+)**: Embed reports directly in frontend (no external Power BI Service navigation)

**Implementation**:
1. Install Power BI Embedded SDK:
   ```bash
   npm install powerbi-client powerbi-client-react
   ```

2. Create embedded component:
   ```typescript
   import { PowerBIEmbed } from 'powerbi-client-react';
   import { models } from 'powerbi-client';
   
   const EmbeddedDashboard: React.FC = () => {
     const embedConfig: models.IReportEmbedConfiguration = {
       type: 'report',
       id: 'REPORT-ID',
       embedUrl: 'EMBED-URL',
       accessToken: 'EMBED-TOKEN',  // Get from backend API
       tokenType: models.TokenType.Embed,
       settings: {
         panes: { filters: { visible: false } },
         background: models.BackgroundType.Transparent
       }
     };
     
     return <PowerBIEmbed embedConfig={embedConfig} />;
   };
   ```

3. Backend API to generate embed tokens:
   ```python
   # backend/src/api/powerbi.py
   from fastapi import APIRouter, Depends
   from azure.identity import DefaultAzureCredential
   from msal import ConfidentialClientApplication
   
   @router.post("/api/powerbi/embed-token")
   async def generate_embed_token(report_id: str, user: User = Depends(get_current_user)):
       # Generate Power BI embed token with RLS filters
       # Apply user's customer_id list to RLS
       pass
   ```

**Benefits of Embedding**:
- Unified user experience (no separate Power BI login)
- Programmatic filtering (auto-filter to user's customers)
- Custom navigation and branding
- Better mobile experience

## Maintenance Notes

**Ownership**: Frontend team (primary), Customer Success team (UX feedback)  
**Update Frequency**: Quarterly review of dashboard links and role mappings  
**Documentation**: Update this file if new dashboards added or roles change  
**Testing**: Regression test all 4 test cases before each release
