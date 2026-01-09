# Customer Recommendation Engine - Deployment Guide

## Prerequisites

Before deploying the Customer Recommendation Engine, ensure you have the following:

### Azure Resources
- **Azure Subscription** with Owner or Contributor access
- **Azure CLI** installed (`az --version` >= 2.50.0)
- **Azure Developer CLI** (azd) installed (`azd version` >= 1.5.0)
- **PowerShell 7+** for running deployment scripts

### Service Principals & Permissions
- Service Principal with permissions to create:
  - Resource Groups
  - Azure Container Apps / App Service
  - Azure Cosmos DB
  - Azure Cache for Redis
  - Azure Key Vault
  - Azure Monitor / Application Insights
  - Azure AD App Registrations (for authentication)

### Local Development Tools
- **Python 3.11+** with pip
- **Node.js 18+** with npm
- **Docker Desktop** (for local container testing)
- **Git** for source control

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Azure Front Door (Optional)               │
└──────────────────────┬──────────────────────────────────────┘
                       │
       ┌───────────────┴───────────────┐
       │                               │
┌──────▼──────┐               ┌───────▼──────┐
│  Frontend   │               │   Backend    │
│  (React)    │               │   (FastAPI)  │
│ Static Web  │               │ Container    │
│    App      │               │    Apps      │
└─────────────┘               └──────┬───────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
             ┌──────▼──────┐  ┌─────▼─────┐   ┌─────▼─────┐
             │  Cosmos DB  │  │   Redis   │   │ Key Vault │
             │  (NoSQL)    │  │  (Cache)  │   │ (Secrets) │
             └─────────────┘  └───────────┘   └───────────┘
                    │
             ┌──────▼──────┐
             │ Application │
             │  Insights   │
             │ (Monitoring)│
             └─────────────┘
```

---

## Deployment Steps

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/AdieuIQ.git
cd AdieuIQ
```

### Step 2: Azure Login

```bash
# Login to Azure CLI
az login

# Set subscription
az account set --subscription "Your-Subscription-ID"

# Login to Azure Developer CLI
azd auth login
```

### Step 3: Configure Environment Variables

Create a `.azure/environment.env` file:

```env
# Environment
ENVIRONMENT=prod
LOCATION=eastus

# Resource Naming
RESOURCE_GROUP_NAME=rg-adieuiq-prod
APP_NAME=adieuiq

# Azure AD Authentication
AZURE_AD_TENANT_ID=your-tenant-id
AZURE_AD_CLIENT_ID=your-client-id
AZURE_AD_AUTHORITY=https://login.microsoftonline.com/your-tenant-id

# Backend Configuration
BACKEND_CONTAINER_IMAGE=adieuiq-backend:latest
BACKEND_PORT=8000

# Frontend Configuration
FRONTEND_CONTAINER_IMAGE=adieuiq-frontend:latest
FRONTEND_PORT=3000

# Cosmos DB
COSMOS_DB_ACCOUNT_NAME=cosmos-adieuiq-prod
COSMOS_DB_DATABASE_NAME=adieuiq

# Redis Cache
REDIS_CACHE_NAME=redis-adieuiq-prod
REDIS_CACHE_SKU=Standard
REDIS_CACHE_CAPACITY=1

# Key Vault
KEY_VAULT_NAME=kv-adieuiq-prod

# Application Insights
APP_INSIGHTS_NAME=appi-adieuiq-prod
```

### Step 4: Deploy Infrastructure

```bash
# Navigate to infrastructure directory
cd infrastructure

# Deploy using Bicep
az deployment sub create \
  --location eastus \
  --template-file bicep/main.bicep \
  --parameters @parameters.prod.json

# Or use deployment script
./scripts/deploy.sh prod
```

The Bicep deployment will create:
- Resource Group
- Cosmos DB account with containers:
  - `customers`
  - `recommendations`
  - `interaction-events`
  - `agent-contributions`
- Azure Cache for Redis
- Azure Key Vault
- Application Insights
- Azure Container Apps (Backend & Frontend)
- Virtual Network & Managed Identity

### Step 5: Configure Key Vault Secrets

```bash
# Set Key Vault name
VAULT_NAME="kv-adieuiq-prod"

# Store Fabric IQ endpoint
az keyvault secret set \
  --vault-name $VAULT_NAME \
  --name "FabricIQ-Endpoint" \
  --value "https://fabriciq.api.microsoft.com"

# Store Foundry IQ endpoint
az keyvault secret set \
  --vault-name $VAULT_NAME \
  --name "FoundryIQ-Endpoint" \
  --value "https://foundryiq.api.microsoft.com"

# Store Azure OpenAI endpoint
az keyvault secret set \
  --vault-name $VAULT_NAME \
  --name "AzureOpenAI-Endpoint" \
  --value "https://your-openai-resource.openai.azure.com"

# Redis access key (auto-retrieved during deployment)
# Cosmos DB key (auto-retrieved during deployment)
```

### Step 6: Build and Deploy Backend

```bash
cd backend

# Build Docker image
docker build -t adieuiq-backend:latest .

# Tag for Azure Container Registry
docker tag adieuiq-backend:latest youracr.azurecr.io/adieuiq-backend:latest

# Push to ACR
az acr login --name youracr
docker push youracr.azurecr.io/adieuiq-backend:latest

# Update Container App
az containerapp update \
  --name ca-adieuiq-backend \
  --resource-group rg-adieuiq-prod \
  --image youracr.azurecr.io/adieuiq-backend:latest
```

### Step 7: Build and Deploy Frontend

```bash
cd frontend

# Install dependencies
npm install

# Build production bundle
npm run build

# Build Docker image
docker build -t adieuiq-frontend:latest .

# Tag and push to ACR
docker tag adieuiq-frontend:latest youracr.azurecr.io/adieuiq-frontend:latest
docker push youracr.azurecr.io/adieuiq-frontend:latest

# Update Container App
az containerapp update \
  --name ca-adieuiq-frontend \
  --resource-group rg-adieuiq-prod \
  --image youracr.azurecr.io/adieuiq-frontend:latest
```

### Step 8: Configure Azure AD Authentication

#### Create App Registration

```bash
# Create Azure AD app registration for backend API
az ad app create \
  --display-name "AdieuIQ Backend API" \
  --identifier-uris "api://adieuiq" \
  --app-roles @backend-app-roles.json

# Get Application ID
BACKEND_APP_ID=$(az ad app list --display-name "AdieuIQ Backend API" --query "[0].appId" -o tsv)

# Create service principal
az ad sp create --id $BACKEND_APP_ID

# Create app registration for frontend SPA
az ad app create \
  --display-name "AdieuIQ Frontend SPA" \
  --spa-redirect-uris "https://your-frontend-url.azurecontainerapps.io" \
  --required-resource-accesses @frontend-resource-access.json

FRONTEND_APP_ID=$(az ad app list --display-name "AdieuIQ Frontend SPA" --query "[0].appId" -o tsv)
```

#### Configure RBAC Scopes

Edit `backend-app-roles.json`:

```json
[
  {
    "allowedMemberTypes": ["User"],
    "description": "Read customer data",
    "displayName": "Customers.Read",
    "id": "generate-guid-1",
    "isEnabled": true,
    "value": "Customers.Read"
  },
  {
    "allowedMemberTypes": ["User"],
    "description": "Generate recommendations",
    "displayName": "Recommendations.Generate",
    "id": "generate-guid-2",
    "isEnabled": true,
    "value": "Recommendations.Generate"
  },
  {
    "allowedMemberTypes": ["User"],
    "description": "View historical interactions",
    "displayName": "History.Read",
    "id": "generate-guid-3",
    "isEnabled": true,
    "value": "History.Read"
  }
]
```

#### Assign Roles to Users

```bash
# Get object IDs of users/groups
USER_ID=$(az ad user show --id user@yourdomain.com --query id -o tsv)

# Assign roles
az ad app role assignment create \
  --id $BACKEND_APP_ID \
  --role "Customers.Read" \
  --assignee $USER_ID

az ad app role assignment create \
  --id $BACKEND_APP_ID \
  --role "Recommendations.Generate" \
  --assignee $USER_ID
```

### Step 9: Configure Managed Identity Permissions

```bash
# Get Managed Identity principal ID
MI_PRINCIPAL_ID=$(az containerapp show \
  --name ca-adieuiq-backend \
  --resource-group rg-adieuiq-prod \
  --query identity.principalId -o tsv)

# Grant Cosmos DB access
az cosmosdb sql role assignment create \
  --account-name cosmos-adieuiq-prod \
  --resource-group rg-adieuiq-prod \
  --role-definition-name "Cosmos DB Built-in Data Contributor" \
  --principal-id $MI_PRINCIPAL_ID \
  --scope "/"

# Grant Key Vault access
az keyvault set-policy \
  --name kv-adieuiq-prod \
  --object-id $MI_PRINCIPAL_ID \
  --secret-permissions get list
```

### Step 10: Verify Deployment

```bash
# Check backend health
curl https://ca-adieuiq-backend.azurecontainerapps.io/health

# Check frontend
curl https://ca-adieuiq-frontend.azurecontainerapps.io

# View logs
az containerapp logs show \
  --name ca-adieuiq-backend \
  --resource-group rg-adieuiq-prod \
  --follow
```

---

## Post-Deployment Configuration

### Enable Application Insights Alerts

```bash
# Create alert for high latency
az monitor metrics alert create \
  --name "Backend High Latency" \
  --resource-group rg-adieuiq-prod \
  --scopes "/subscriptions/.../resourceGroups/rg-adieuiq-prod/providers/Microsoft.Insights/components/appi-adieuiq-prod" \
  --condition "avg requests/duration > 2000" \
  --description "Backend API response time >2s" \
  --window-size 5m \
  --evaluation-frequency 1m
```

### Configure Auto-scaling

```bash
# Scale backend based on CPU
az containerapp update \
  --name ca-adieuiq-backend \
  --resource-group rg-adieuiq-prod \
  --min-replicas 2 \
  --max-replicas 10 \
  --scale-rule-name "cpu-scale" \
  --scale-rule-type "cpu" \
  --scale-rule-metadata "type=Utilization" "value=70"
```

### Enable Diagnostic Logs

```bash
# Send logs to Log Analytics
az monitor diagnostic-settings create \
  --name "Backend Diagnostics" \
  --resource "/subscriptions/.../resourceGroups/rg-adieuiq-prod/providers/Microsoft.App/containerApps/ca-adieuiq-backend" \
  --logs '[{"category": "ContainerAppConsoleLogs", "enabled": true}]' \
  --metrics '[{"category": "AllMetrics", "enabled": true}]' \
  --workspace "/subscriptions/.../resourceGroups/rg-adieuiq-prod/providers/Microsoft.OperationalInsights/workspaces/log-adieuiq-prod"
```

---

## Troubleshooting

### Backend Container Won't Start

**Issue**: Container crashes on startup

**Diagnosis**:
```bash
az containerapp logs show --name ca-adieuiq-backend --resource-group rg-adieuiq-prod --tail 100
```

**Common Causes**:
1. Missing environment variables (check `COSMOS_DB_ENDPOINT`, `KEY_VAULT_NAME`)
2. Managed Identity permissions not configured
3. Key Vault secrets not set

**Solution**:
```bash
# Verify environment variables
az containerapp show --name ca-adieuiq-backend --resource-group rg-adieuiq-prod --query properties.configuration.secrets

# Check Managed Identity
az containerapp identity show --name ca-adieuiq-backend --resource-group rg-adieuiq-prod
```

### Authentication Failures

**Issue**: 401 Unauthorized errors

**Diagnosis**:
- Check Azure AD app registration configuration
- Verify redirect URIs match deployed URLs
- Ensure RBAC roles are assigned

**Solution**:
```bash
# Verify app registration
az ad app show --id $BACKEND_APP_ID

# Check role assignments
az ad app role assignment list --id $BACKEND_APP_ID
```

### Cosmos DB Connection Errors

**Issue**: `CosmosDBConnectionError` in logs

**Diagnosis**:
```bash
# Check Managed Identity has Cosmos DB permissions
az cosmosdb sql role assignment list \
  --account-name cosmos-adieuiq-prod \
  --resource-group rg-adieuiq-prod
```

**Solution**:
```bash
# Re-assign permissions (see Step 9)
az cosmosdb sql role assignment create ...
```

### Redis Cache Connection Issues

**Issue**: Redis timeout or connection refused

**Diagnosis**:
- Check if Redis is in same VNet as Container Apps
- Verify firewall rules allow Container App subnet

**Solution**:
```bash
# Update Redis firewall rules
az redis firewall-rules create \
  --name allow-container-apps \
  --resource-group rg-adieuiq-prod \
  --redis-name redis-adieuiq-prod \
  --start-ip 10.0.0.0 \
  --end-ip 10.0.255.255
```

---

## Monitoring & Maintenance

### Key Metrics to Monitor

1. **API Latency**: p95 < 2s (per SC-003)
2. **Error Rate**: < 1%
3. **Cache Hit Rate**: > 80%
4. **Cosmos DB RU consumption**: Monitor for throttling
5. **Container CPU/Memory**: Scale if consistently > 70%

### Log Queries (KQL)

#### Find Failed Recommendations
```kql
traces
| where customDimensions.["span.name"] == "recommendation_service.generate"
| where customDimensions.["error"] != ""
| project timestamp, customDimensions.["customer_id"], customDimensions.["error"]
| order by timestamp desc
```

#### Track Cache Performance
```kql
traces
| where message contains "Cache HIT" or message contains "Cache MISS"
| summarize hits=countif(message contains "HIT"), misses=countif(message contains "MISS") by bin(timestamp, 1h)
| extend hit_rate = hits * 100.0 / (hits + misses)
```

---

## Rollback Procedure

If deployment issues occur:

```bash
# Rollback backend to previous version
az containerapp revision list \
  --name ca-adieuiq-backend \
  --resource-group rg-adieuiq-prod

# Activate previous revision
az containerapp revision activate \
  --revision ca-adieuiq-backend--<revision-id> \
  --resource-group rg-adieuiq-prod
```

---

## Security Checklist

- [ ] Managed Identity enabled for all services
- [ ] No hardcoded secrets in code or configuration
- [ ] Azure AD authentication configured
- [ ] RBAC roles assigned per principle of least privilege
- [ ] Key Vault access policies configured
- [ ] Redis SSL/TLS enabled
- [ ] Cosmos DB firewall rules configured
- [ ] Application Insights instrumented
- [ ] Diagnostic logs enabled
- [ ] Auto-scaling configured
- [ ] Alerts configured for critical metrics

---

## Support Contacts

- **DevOps Lead**: devops@company.com
- **Security Team**: security@company.com
- **Azure Support**: https://portal.azure.com/#blade/Microsoft_Azure_Support/HelpAndSupportBlade

---

## References

- [Azure Container Apps Documentation](https://learn.microsoft.com/azure/container-apps/)
- [Azure Cosmos DB Best Practices](https://learn.microsoft.com/azure/cosmos-db/best-practices)
- [Azure Cache for Redis](https://learn.microsoft.com/azure/azure-cache-for-redis/)
- [Azure AD Authentication](https://learn.microsoft.com/azure/active-directory/develop/)
- [Application Insights](https://learn.microsoft.com/azure/azure-monitor/app/app-insights-overview)
