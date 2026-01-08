"""
Core configuration management for Customer Recommendation Engine.
Constitutional Principle II: Load secrets from Key Vault, never hardcode credentials.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


class Settings(BaseSettings):
    """Application settings loaded from environment variables and Key Vault."""
    
    # Environment
    environment: str = "dev"
    
    # Azure Resources
    key_vault_name: str
    cosmos_db_endpoint: str
    redis_hostname: str
    
    # Application Insights
    applicationinsights_connection_string: str
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    
    # CORS Origins (comma-separated)
    cors_origins: str = "*"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class KeyVaultSecrets:
    """Secrets loaded from Azure Key Vault using Managed Identity."""
    
    def __init__(self, key_vault_name: str):
        self.credential = DefaultAzureCredential()
        vault_url = f"https://{key_vault_name}.vault.azure.net"
        self.client = SecretClient(vault_url=vault_url, credential=self.credential)
    
    @property
    def fabric_iq_endpoint(self) -> str:
        """Fabric IQ service endpoint."""
        return self._get_secret("FabricIQ-Endpoint")
    
    @property
    def foundry_iq_endpoint(self) -> str:
        """Foundry IQ service endpoint."""
        return self._get_secret("FoundryIQ-Endpoint")
    
    @property
    def azure_openai_endpoint(self) -> str:
        """Azure OpenAI service endpoint."""
        return self._get_secret("AzureOpenAI-Endpoint")
    
    @property
    def redis_access_key(self) -> str:
        """Redis Cache access key."""
        return self._get_secret("Redis-AccessKey")
    
    @property
    def cosmos_db_key(self) -> str:
        """Cosmos DB master key."""
        return self._get_secret("CosmosDB-Key")
    
    def _get_secret(self, name: str) -> str:
        """Retrieve secret from Key Vault."""
        try:
            secret = self.client.get_secret(name)
            return secret.value
        except Exception as e:
            raise ValueError(f"Failed to retrieve secret '{name}' from Key Vault: {e}")


# Global configuration instances
settings = Settings()
secrets: Optional[KeyVaultSecrets] = None

def initialize_secrets():
    """Initialize Key Vault secrets client (call during app startup)."""
    global secrets
    secrets = KeyVaultSecrets(settings.key_vault_name)


def get_settings() -> Settings:
    """Get application settings."""
    return settings


def get_secrets() -> KeyVaultSecrets:
    """Get Key Vault secrets."""
    if secrets is None:
        raise RuntimeError("Secrets not initialized. Call initialize_secrets() during startup.")
    return secrets
