// Monitoring infrastructure: Log Analytics + Application Insights
// Constitutional Principle IV: Observability & Monitoring

param location string
param environment string
param logAnalyticsName string
param appInsightsName string

// Environment-specific retention configuration for cost optimization
// Note: PerGB2018 SKU requires minimum 30 days retention or 7 days (but must be 30-730 days)
var retentionConfig = {
  dev: 30      // 30-day minimum for PerGB2018 SKU
  staging: 30  // 30-day retention for staging
  prod: 30     // 30-day retention for production (~$12.50/month for 5GB)
}

var retentionDays = retentionConfig[environment]

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  tags: {
    Environment: environment
    Purpose: 'Centralized Logging'
  }
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: retentionDays
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  tags: {
    Environment: environment
    Purpose: 'Application Performance Monitoring'
  }
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

output logAnalyticsWorkspaceId string = logAnalytics.id
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
