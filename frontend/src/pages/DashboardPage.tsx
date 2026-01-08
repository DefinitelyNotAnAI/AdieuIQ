import React from 'react';
import DashboardLinks from '../components/DashboardLinks/DashboardLinks';

/**
 * DashboardPage - Example page showing Power BI dashboard links
 * 
 * Usage in App.tsx or routing:
 * <Route path="/dashboards" element={<DashboardPage />} />
 * 
 * Requires:
 * - User authentication via MSAL (Azure AD)
 * - JWT token with roles claim
 */

const DashboardPage: React.FC = () => {
  // TODO: Replace with actual user roles from JWT token
  // Example: Extract from MSAL useAccount() hook
  // const account = useAccount();
  // const userRoles = account?.idTokenClaims?.roles || [];
  
  // Mock user roles for demonstration
  // In production, this should come from Azure AD JWT token claims
  const userRoles = ['CustomerSuccessManager']; // or ['Administrator'], ['SupportAgent']

  // TODO: Replace with actual Power BI workspace URL from environment config
  // Example: process.env.REACT_APP_POWERBI_WORKSPACE_URL
  const powerBiWorkspaceUrl = 'https://app.powerbi.com/groups/YOUR-WORKSPACE-ID-HERE';

  return (
    <div className="dashboard-page">
      <DashboardLinks 
        userRoles={userRoles}
        powerBiWorkspaceUrl={powerBiWorkspaceUrl}
      />
    </div>
  );
};

export default DashboardPage;
