// Cosmos DB for recommendation cache and history storage

param location string
param environment string
param accountName string

resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' = {
  name: accountName
  location: location
  tags: {
    Environment: environment
    Purpose: 'Recommendation Cache and History'
  }
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    enableAutomaticFailover: false
    enableMultipleWriteLocations: false
    capabilities: [
      {
        name: 'EnableServerless'  // Serverless for cost optimization in dev/staging
      }
    ]
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-04-15' = {
  parent: cosmosDbAccount
  name: 'adieuiq-db'
  properties: {
    resource: {
      id: 'adieuiq-db'
    }
  }
}

resource customersContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: database
  name: 'customers'
  properties: {
    resource: {
      id: 'customers'
      partitionKey: {
        paths: [
          '/account_id'
        ]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
      }
    }
  }
}

resource recommendationsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: database
  name: 'recommendations'
  properties: {
    resource: {
      id: 'recommendations'
      partitionKey: {
        paths: [
          '/customer_id'
        ]
        kind: 'Hash'
      }
      defaultTtl: 31536000  // 12 months retention per FR-013
    }
  }
}

resource interactionEventsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: database
  name: 'interaction-events'
  properties: {
    resource: {
      id: 'interaction-events'
      partitionKey: {
        paths: [
          '/customer_id'
        ]
        kind: 'Hash'
      }
      defaultTtl: 31536000  // 12 months retention
    }
  }
}

output cosmosDbEndpoint string = cosmosDbAccount.properties.documentEndpoint
output cosmosDbAccountName string = cosmosDbAccount.name
