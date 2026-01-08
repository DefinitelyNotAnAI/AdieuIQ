// App Service for FastAPI backend
// Constitutional Principle II: Managed Identity for authentication

param location string
param environment string
param appServicePlanName string
param appServiceName string
param keyVaultName string
param appInsightsConnectionString string
param cosmosDbEndpoint string
param redisHostname string

resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: appServicePlanName
  location: location
  tags: {
    Environment: environment
    Purpose: 'Backend API Hosting'
  }
  kind: 'linux'
  sku: {
    name: 'P1v3'  // Premium tier for production readiness
    tier: 'PremiumV3'
    capacity: 1
  }
  properties: {
    reserved: true  // Linux
  }
}

resource appService 'Microsoft.Web/sites@2023-01-01' = {
  name: appServiceName
  location: location
  tags: {
    Environment: environment
    Purpose: 'FastAPI Backend'
  }
  identity: {
    type: 'SystemAssigned'  // Enable Managed Identity per constitutional requirement
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      alwaysOn: true
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appSettings: [
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsightsConnectionString
        }
        {
          name: 'KEY_VAULT_NAME'
          value: keyVaultName
        }
        {
          name: 'COSMOS_DB_ENDPOINT'
          value: cosmosDbEndpoint
        }
        {
          name: 'REDIS_HOSTNAME'
          value: redisHostname
        }
        {
          name: 'ENVIRONMENT'
          value: environment
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
      ]
      cors: {
        allowedOrigins: [
          '*'  // In production, restrict to specific frontend domains
        ]
      }
    }
  }
}

output appServiceName string = appService.name
output appServicePrincipalId string = appService.identity.principalId
output appServiceUrl string = 'https://${appService.properties.defaultHostName}'
