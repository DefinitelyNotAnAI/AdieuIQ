# Deployment script for Customer Recommendation Engine infrastructure
# Usage: .\deploy.ps1 -Environment dev|staging|prod -Location eastus [-ResourceSuffix custom-suffix]

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('dev', 'staging', 'prod')]
    [string]$Environment = 'dev',
    
    [Parameter(Mandatory=$false)]
    [string]$Location = 'eastus',
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceSuffix = $null
)

$ErrorActionPreference = 'Stop'

# Generate default resource suffix if not provided: demo-{location}-{date}
if (-not $ResourceSuffix) {
    $dateString = Get-Date -Format 'yyyyMMdd'
    $ResourceSuffix = "demo-$Location-$dateString"
}

Write-Host "🚀 Deploying AdieuIQ Customer Recommendation Engine" -ForegroundColor Cyan
Write-Host "Environment: $Environment" -ForegroundColor Yellow
Write-Host "Location: $Location" -ForegroundColor Yellow
Write-Host "Resource Suffix: $ResourceSuffix" -ForegroundColor Yellow
Write-Host ""

# Validate Azure CLI is installed
try {
    $azVersion = az --version 2>&1
    Write-Host "✅ Azure CLI found" -ForegroundColor Green
} catch {
    Write-Host "❌ Azure CLI not found. Please install: https://learn.microsoft.com/cli/azure/install-azure-cli" -ForegroundColor Red
    exit 1
}

# Check Azure login
Write-Host "✅ Checking Azure login..." -ForegroundColor Green
try {
    $account = az account show 2>&1 | ConvertFrom-Json
    Write-Host "   Logged in as: $($account.user.name)" -ForegroundColor Gray
    Write-Host "   Subscription: $($account.name)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Not logged in to Azure. Running az login..." -ForegroundColor Yellow
    az login
    $account = az account show 2>&1 | ConvertFrom-Json
}

# Deploy infrastructure
Write-Host ""
Write-Host "📦 Deploying infrastructure..." -ForegroundColor Cyan
$deploymentName = "adieuiq-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
$bicepFile = Join-Path $PSScriptRoot "..\bicep\main.bicep"

Write-Host "   Deployment name: $deploymentName" -ForegroundColor Gray
Write-Host "   Template: $bicepFile" -ForegroundColor Gray
Write-Host ""

try {
    # Run deployment with debug output visible in terminal
    az deployment sub create `
        --name $deploymentName `
        --location $Location `
        --template-file $bicepFile `
        --parameters environment=$Environment location=$Location resourceSuffix=$ResourceSuffix `
        --debug
    
    Write-Host ""
    Write-Host "📊 Fetching deployment outputs..." -ForegroundColor Cyan
    
    $deployment = az deployment sub show `
        --name $deploymentName `
        --query 'properties.outputs' `
        -o json | ConvertFrom-Json
    
    Write-Host "✅ Infrastructure deployment complete!" -ForegroundColor Green
} catch {
    Write-Host "❌ Infrastructure deployment failed!" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Extract outputs
Write-Host ""
Write-Host "📄 Retrieving deployment outputs..." -ForegroundColor Cyan

$resourceGroupName = $deployment.resourceGroupName.value
$keyVaultName = $deployment.keyVaultName.value
$appServiceName = $deployment.appServiceName.value
$cosmosDbEndpoint = $deployment.cosmosDbEndpoint.value
$cosmosDbName = $deployment.cosmosDbAccountName.value
$redisHostname = $deployment.redisHostname.value
$redisName = $deployment.redisCacheName.value
$appInsightsConnectionString = $deployment.appInsightsConnectionString.value

Write-Host ""
Write-Host "✅ Deployment outputs:" -ForegroundColor Green
Write-Host "   Resource Group: $resourceGroupName" -ForegroundColor Gray
Write-Host "   Key Vault: $keyVaultName" -ForegroundColor Gray
Write-Host "   App Service: $appServiceName" -ForegroundColor Gray
Write-Host "   Cosmos DB: $cosmosDbName" -ForegroundColor Gray
Write-Host "   Cosmos Endpoint: $cosmosDbEndpoint" -ForegroundColor Gray
Write-Host "   Redis Cache: $redisName" -ForegroundColor Gray
Write-Host "   Redis Hostname: $redisHostname" -ForegroundColor Gray
Write-Host ""

# Store connection strings in Key Vault
Write-Host "🔐 Storing connection strings in Key Vault..." -ForegroundColor Cyan

# Get Cosmos DB connection string
$cosmosKey = az cosmosdb keys list `
    --name $cosmosDbName `
    --resource-group $resourceGroupName `
    --query primaryMasterKey `
    -o tsv

$cosmosConnectionString = "AccountEndpoint=https://$cosmosDbName.documents.azure.com:443/;AccountKey=$cosmosKey;"

az keyvault secret set `
    --vault-name $keyVaultName `
    --name "CosmosDB-ConnectionString" `
    --value $cosmosConnectionString `
    -o none

Write-Host "   ✓ CosmosDB connection string stored" -ForegroundColor Gray

# Get Redis connection string
$redisKey = az redis list-keys `
    --name $redisName `
    --resource-group $resourceGroupName `
    --query primaryKey `
    -o tsv

$redisConnectionString = "$redisName.redis.cache.windows.net:6380,password=$redisKey,ssl=True,abortConnect=False"

az keyvault secret set `
    --vault-name $keyVaultName `
    --name "Redis-ConnectionString" `
    --value $redisConnectionString `
    -o none

# Store individual Redis components
az keyvault secret set --vault-name $keyVaultName --name "REDIS-HOSTNAME" --value "$redisName.redis.cache.windows.net" -o none
az keyvault secret set --vault-name $keyVaultName --name "REDIS-PORT" --value "6380" -o none
az keyvault secret set --vault-name $keyVaultName --name "REDIS-ACCESS-KEY" --value $redisKey -o none

Write-Host "   ✓ Redis connection string stored" -ForegroundColor Gray

# Get Application Insights connection string (already retrieved from deployment outputs)
az keyvault secret set `
    --vault-name $keyVaultName `
    --name "ApplicationInsights-ConnectionString" `
    --value $appInsightsConnectionString `
    -o none

Write-Host "   ✓ Application Insights connection string stored" -ForegroundColor Gray

Write-Host ""
Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host ""

# Save outputs to file
$outputFile = Join-Path $PSScriptRoot "deployment-outputs.json"
$outputs = @{
    environment = $Environment
    location = $Location
    resourceGroupName = $resourceGroupName
    keyVaultName = $keyVaultName
    appServiceName = $appServiceName
    cosmosDbName = $cosmosDbName
    cosmosDbEndpoint = $cosmosDbEndpoint
    redisName = $redisName
    redisHostname = $redisHostname
    deploymentDate = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
} | ConvertTo-Json

$outputs | Out-File -FilePath $outputFile -Encoding UTF8
Write-Host "📄 Deployment outputs saved to: $outputFile" -ForegroundColor Cyan
Write-Host ""

# Next steps
Write-Host "📝 Next Steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Configure external service endpoints in Key Vault:" -ForegroundColor White
Write-Host "   az keyvault secret set --vault-name $keyVaultName --name 'FabricIQ-Endpoint' --value '<your-fabric-iq-url>'"
Write-Host "   az keyvault secret set --vault-name $keyVaultName --name 'FoundryIQ-Endpoint' --value '<your-foundry-iq-url>'"
Write-Host "   az keyvault secret set --vault-name $keyVaultName --name 'AzureOpenAI-Endpoint' --value '<your-openai-endpoint>'"
Write-Host "   az keyvault secret set --vault-name $keyVaultName --name 'AzureOpenAI-ApiKey' --value '<your-openai-key>'"
Write-Host ""
Write-Host "2. Deploy backend application:" -ForegroundColor White
Write-Host "   cd backend"
Write-Host "   az webapp up --name $appServiceName --resource-group $resourceGroupName --runtime 'PYTHON:3.11'"
Write-Host ""
Write-Host "3. Configure Azure AD authentication:" -ForegroundColor White
Write-Host "   See infrastructure/README.md for detailed steps"
Write-Host ""
Write-Host "4. Deploy frontend:" -ForegroundColor White
Write-Host "   cd frontend"
Write-Host "   npm install && npm run build"
Write-Host "   # Deploy to Azure Static Web Apps"
Write-Host ""
Write-Host "🎉 Happy deploying!" -ForegroundColor Cyan
