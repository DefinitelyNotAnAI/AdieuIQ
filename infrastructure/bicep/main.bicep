// Main Bicep template for Customer Recommendation Engine
// Deploys all Azure resources required per constitutional principles

targetScope = 'subscription'

@description('Azure region for all resources')
param location string = 'eastus'

@description('Environment name (dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('Unique suffix for resource names')
param resourceSuffix string = uniqueString(subscription().subscriptionId, environment)

// Resource naming
var resourceGroupName = 'rg-adieuiq-${environment}-${resourceSuffix}'
var keyVaultName = 'kv-adieuiq-${environment}-${substring(resourceSuffix, 0, 6)}'
var appServicePlanName = 'asp-adieuiq-${environment}-${resourceSuffix}'
var appServiceName = 'app-adieuiq-api-${environment}-${resourceSuffix}'
var containerAppsEnvName = 'cae-adieuiq-${environment}-${resourceSuffix}'
var cosmosDbAccountName = 'cosmos-adieuiq-${environment}-${resourceSuffix}'
var redisCacheName = 'redis-adieuiq-${environment}-${resourceSuffix}'
var appInsightsName = 'appi-adieuiq-${environment}-${resourceSuffix}'
var logAnalyticsName = 'log-adieuiq-${environment}-${resourceSuffix}'

// Create resource group
resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: resourceGroupName
  location: location
  tags: {
    Environment: environment
    Application: 'AdieuIQ'
    ManagedBy: 'Bicep'
  }
}

// Deploy monitoring infrastructure
module monitoring './monitoring.bicep' = {
  scope: rg
  name: 'monitoring-deployment'
  params: {
    location: location
    environment: environment
    logAnalyticsName: logAnalyticsName
    appInsightsName: appInsightsName
  }
}

// Deploy Key Vault
module keyVault './key-vault.bicep' = {
  scope: rg
  name: 'keyvault-deployment'
  params: {
    location: location
    environment: environment
    keyVaultName: keyVaultName
  }
}

// Deploy Cosmos DB
module cosmosDb './cosmos-db.bicep' = {
  scope: rg
  name: 'cosmosdb-deployment'
  params: {
    location: location
    environment: environment
    accountName: cosmosDbAccountName
  }
}

// Deploy Redis Cache
module redisCache './redis-cache.bicep' = {
  scope: rg
  name: 'redis-deployment'
  params: {
    location: location
    environment: environment
    redisCacheName: redisCacheName
  }
}

// Deploy App Service for backend API
module appService './app-service.bicep' = {
  scope: rg
  name: 'appservice-deployment'
  params: {
    location: location
    environment: environment
    appServicePlanName: appServicePlanName
    appServiceName: appServiceName
    keyVaultName: keyVaultName
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    cosmosDbEndpoint: cosmosDb.outputs.cosmosDbEndpoint
    redisHostname: redisCache.outputs.redisHostname
  }
  dependsOn: [
    keyVault
    monitoring
    cosmosDb
    redisCache
  ]
}

// Deploy Container Apps environment for agent orchestration
module containerApps './container-apps.bicep' = {
  scope: rg
  name: 'containerapps-deployment'
  params: {
    location: location
    environment: environment
    containerAppsEnvName: containerAppsEnvName
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
  }
  dependsOn: [
    monitoring
  ]
}

// Outputs
output resourceGroupName string = rg.name
output keyVaultName string = keyVault.outputs.keyVaultName
output appServiceName string = appService.outputs.appServiceName
output appServiceUrl string = appService.outputs.appServiceUrl
output cosmosDbEndpoint string = cosmosDb.outputs.cosmosDbEndpoint
output cosmosDbAccountName string = cosmosDb.outputs.cosmosDbAccountName
output redisHostname string = redisCache.outputs.redisHostname
output redisCacheName string = redisCache.outputs.redisName
output appInsightsInstrumentationKey string = monitoring.outputs.appInsightsInstrumentationKey
output appInsightsConnectionString string = monitoring.outputs.appInsightsConnectionString
