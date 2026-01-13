// Azure Redis Cache for session and performance optimization

param location string
param environment string
param redisCacheName string

// Environment-specific SKU configuration for cost optimization
var skuConfig = {
  dev: {
    name: 'Basic'  // Basic tier for dev/demo: 250MB (~$16/month)
    family: 'C'
    capacity: 0  // C0 = 250MB
  }
  staging: {
    name: 'Basic'  // Basic tier for staging/demo: 250MB (~$16/month)
    family: 'C'
    capacity: 0  // C0 = 250MB
  }
  prod: {
    name: 'Standard'  // Standard tier for production: 1GB with SLA (~$76/month)
    family: 'C'
    capacity: 1  // C1 = 1GB
  }
}

var selectedSku = skuConfig[environment]

resource redisCache 'Microsoft.Cache/redis@2023-08-01' = {
  name: redisCacheName
  location: location
  tags: {
    Environment: environment
    Purpose: 'Session and Performance Cache'
  }
  properties: {
    sku: {
      name: selectedSku.name
      family: selectedSku.family
      capacity: selectedSku.capacity
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    redisConfiguration: {
      'maxmemory-policy': 'allkeys-lru'  // Evict least recently used keys
    }
  }
}

output redisHostname string = redisCache.properties.hostName
output redisSslPort int = redisCache.properties.sslPort
output redisName string = redisCache.name
