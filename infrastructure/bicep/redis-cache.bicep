// Azure Redis Cache for session and performance optimization

param location string
param environment string
param redisCacheName string

resource redisCache 'Microsoft.Cache/redis@2023-08-01' = {
  name: redisCacheName
  location: location
  tags: {
    Environment: environment
    Purpose: 'Session and Performance Cache'
  }
  properties: {
    sku: {
      name: 'Standard'
      family: 'C'
      capacity: 1  // 1GB Standard tier per plan.md
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
