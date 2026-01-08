#!/bin/bash
# Deployment script for Customer Recommendation Engine infrastructure
# Usage: ./deploy.sh [dev|staging|prod]

set -e  # Exit on error

ENVIRONMENT=${1:-dev}
LOCATION=${2:-eastus}

echo "🚀 Deploying AdieuIQ Customer Recommendation Engine"
echo "Environment: $ENVIRONMENT"
echo "Location: $LOCATION"
echo ""

# Validate Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found. Please install: https://learn.microsoft.com/cli/azure/install-azure-cli"
    exit 1
fi

# Login check
echo "✅ Checking Azure login..."
az account show &> /dev/null || az login

# Deploy infrastructure
echo "📦 Deploying infrastructure..."
DEPLOYMENT_NAME="adieuiq-$(date +%Y%m%d-%H%M%S)"

az deployment sub create \
  --name "$DEPLOYMENT_NAME" \
  --location "$LOCATION" \
  --template-file ../bicep/main.bicep \
  --parameters environment="$ENVIRONMENT" location="$LOCATION"

# Get outputs
echo "📄 Retrieving deployment outputs..."
RESOURCE_GROUP=$(az deployment sub show --name "$DEPLOYMENT_NAME" --query properties.outputs.resourceGroupName.value -o tsv)
KEY_VAULT_NAME=$(az deployment sub show --name "$DEPLOYMENT_NAME" --query properties.outputs.keyVaultName.value -o tsv)
APP_SERVICE_NAME=$(az deployment sub show --name "$DEPLOYMENT_NAME" --query properties.outputs.appServiceName.value -o tsv)

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Resource Group: $RESOURCE_GROUP"
echo "Key Vault: $KEY_VAULT_NAME"
echo "App Service: $APP_SERVICE_NAME"
echo ""

# Configure RBAC for App Service Managed Identity
echo "🔐 Configuring RBAC permissions..."

APP_SERVICE_PRINCIPAL_ID=$(az webapp identity show --name "$APP_SERVICE_NAME" --resource-group "$RESOURCE_GROUP" --query principalId -o tsv)

# Grant Key Vault Secrets User role
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee-object-id "$APP_SERVICE_PRINCIPAL_ID" \
  --assignee-principal-type ServicePrincipal \
  --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.KeyVault/vaults/$KEY_VAULT_NAME"

echo "✅ RBAC configured"
echo ""

# Deployment instructions
echo "📝 Next Steps:"
echo "1. Set Key Vault secrets via Azure Portal or CLI:"
echo "   az keyvault secret set --vault-name $KEY_VAULT_NAME --name FabricIQ-Endpoint --value '<your-value>'"
echo "   az keyvault secret set --vault-name $KEY_VAULT_NAME --name FoundryIQ-Endpoint --value '<your-value>'"
echo "   az keyvault secret set --vault-name $KEY_VAULT_NAME --name AzureOpenAI-Endpoint --value '<your-value>'"
echo ""
echo "2. Deploy backend code:"
echo "   cd ../../backend"
echo "   az webapp up --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP --runtime PYTHON:3.11"
echo ""
echo "3. Deploy frontend:"
echo "   cd ../../frontend"
echo "   npm run build"
echo "   # Deploy build/ to Azure Static Web Apps or CDN"
echo ""

exit 0
