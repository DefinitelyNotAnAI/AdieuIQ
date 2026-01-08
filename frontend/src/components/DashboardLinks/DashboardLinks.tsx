import React from 'react';
import './DashboardLinks.css';

/**
 * Dashboard links for Power BI reports
 * Displays links based on user role (RBAC)
 * 
 * Roles:
 * - CustomerSuccessManager: Can access both Adoption Metrics and Upsell Pipeline dashboards
 * - Administrator: Can access both dashboards
 * - SupportAgent: No access (links hidden)
 */

interface DashboardLinksProps {
  userRoles: string[];  // User's Azure AD roles from JWT token
  powerBiWorkspaceUrl?: string;  // Power BI workspace URL (default: production workspace)
}

interface Dashboard {
  id: string;
  name: string;
  description: string;
  reportUrl: string;
  requiredRoles: string[];
  icon: string;
}

const DashboardLinks: React.FC<DashboardLinksProps> = ({ 
  userRoles,
  powerBiWorkspaceUrl = 'https://app.powerbi.com/groups/00000000-0000-0000-0000-000000000000'  // Replace with actual workspace ID
}) => {
  
  // Dashboard definitions
  const dashboards: Dashboard[] = [
    {
      id: 'adoption-metrics',
      name: 'Adoption Metrics',
      description: 'Monitor feature adoption trends and identify low-adoption customers',
      reportUrl: `${powerBiWorkspaceUrl}/reports/adoption-metrics`,
      requiredRoles: ['CustomerSuccessManager', 'Administrator'],
      icon: '📊'
    },
    {
      id: 'upsell-pipeline',
      name: 'Upsell Pipeline',
      description: 'Prioritized upsell opportunities with revenue impact and confidence scores',
      reportUrl: `${powerBiWorkspaceUrl}/reports/upsell-pipeline`,
      requiredRoles: ['CustomerSuccessManager', 'Administrator'],
      icon: '💰'
    }
  ];

  /**
   * Check if user has access to a dashboard based on roles
   * @param requiredRoles - Roles required to access dashboard
   * @returns true if user has at least one required role
   */
  const hasAccess = (requiredRoles: string[]): boolean => {
    return requiredRoles.some(role => userRoles.includes(role));
  };

  // Filter dashboards based on user roles
  const accessibleDashboards = dashboards.filter(dashboard => 
    hasAccess(dashboard.requiredRoles)
  );

  // If user has no dashboard access, don't render component
  if (accessibleDashboards.length === 0) {
    return null;
  }

  return (
    <div className="dashboard-links-container">
      <h2 className="dashboard-links-title">Power BI Dashboards</h2>
      <p className="dashboard-links-subtitle">
        Real-time insights powered by Fabric Real-Time Intelligence
      </p>

      <div className="dashboard-grid">
        {accessibleDashboards.map(dashboard => (
          <a
            key={dashboard.id}
            href={dashboard.reportUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="dashboard-card"
            aria-label={`Open ${dashboard.name} dashboard in new tab`}
          >
            <div className="dashboard-card-header">
              <span className="dashboard-icon" aria-hidden="true">
                {dashboard.icon}
              </span>
              <h3 className="dashboard-name">{dashboard.name}</h3>
            </div>
            <p className="dashboard-description">{dashboard.description}</p>
            <div className="dashboard-card-footer">
              <span className="dashboard-link-label">Open in Power BI</span>
              <span className="dashboard-link-arrow" aria-hidden="true">→</span>
            </div>
          </a>
        ))}
      </div>

      <div className="dashboard-info">
        <p className="dashboard-info-text">
          <strong>Note:</strong> Dashboards refresh automatically every 10 seconds. 
          You'll only see data for customers assigned to you (row-level security applied).
        </p>
      </div>
    </div>
  );
};

export default DashboardLinks;
