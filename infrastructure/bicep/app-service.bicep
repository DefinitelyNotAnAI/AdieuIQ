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

// Environment-specific SKU configuration for cost optimization
var skuConfig = {
  dev: {
    name: 'F1'  // Free tier for dev/demo: No cost, no quota required
    tier: 'Free'
  }
  staging: {
    name: 'B1'  // Basic B1 tier for staging/demo (~$13/month)
    tier: 'Basic'
  }
  prod: {
    name: 'P1v3'  // Premium tier for production readiness (~$146/month)
    tier: 'PremiumV3'
  }
}

var selectedSku = skuConfig[environment]

resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: appServicePlanName
  location: location
  tags: {
    Environment: environment
    Purpose: 'Backend API Hosting'
  }
  kind: 'linux'
  sku: {
    name: selectedSku.name
    tier: selectedSku.tier
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
      alwaysOn: environment == 'prod' ? true : false  // Disable always-on for dev/staging to reduce costs
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
