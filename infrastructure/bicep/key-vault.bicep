// Key Vault for secrets management (Constitutional Principle II)

param location string
param environment string
param keyVaultName string

resource keyVault 'Microsoft.KeyVault/vaults@2023-02-01' = {
  name: keyVaultName
  location: location
  tags: {
    Environment: environment
    Purpose: 'Secrets Management'
  }
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true  // Use RBAC instead of access policies
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    networkAcls: {
      defaultAction: 'Allow'  // In production, restrict to specific VNets
      bypass: 'AzureServices'
    }
  }
}

// Placeholder secrets (actual values set via deployment script or portal)
resource fabricIqEndpointSecret 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  parent: keyVault
  name: 'FabricIQ-Endpoint'
  properties: {
    value: 'PLACEHOLDER_SET_VIA_DEPLOYMENT'
  }
}

resource foundryIqEndpointSecret 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  parent: keyVault
  name: 'FoundryIQ-Endpoint'
  properties: {
    value: 'PLACEHOLDER_SET_VIA_DEPLOYMENT'
  }
}

resource openAiEndpointSecret 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  parent: keyVault
  name: 'AzureOpenAI-Endpoint'
  properties: {
    value: 'PLACEHOLDER_SET_VIA_DEPLOYMENT'
  }
}

output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri
