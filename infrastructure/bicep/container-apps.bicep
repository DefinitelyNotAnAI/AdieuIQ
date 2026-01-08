// Azure Container Apps for agent orchestration service
// Constitutional Principle II: Managed Identity for authentication

param location string
param environment string
param containerAppsEnvName string
param logAnalyticsWorkspaceId string
param appInsightsConnectionString string

resource containerAppsEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: containerAppsEnvName
  location: location
  tags: {
    Environment: environment
    Purpose: 'Agent Orchestration Runtime'
  }
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: reference(logAnalyticsWorkspaceId, '2022-10-01').customerId
        sharedKey: listKeys(logAnalyticsWorkspaceId, '2022-10-01').primarySharedKey
      }
    }
  }
}

// Placeholder for orchestration container app (deployed separately after image build)
output containerAppsEnvId string = containerAppsEnv.id
output containerAppsEnvName string = containerAppsEnv.name
