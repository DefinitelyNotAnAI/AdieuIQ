"""
Azure AD authentication and Managed Identity helper.
Constitutional Principle II: Security & Identity (NON-NEGOTIABLE)
"""

from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
import jwt
from jwt import PyJWKClient


# Security scheme
security = HTTPBearer()

# Azure AD configuration
AZURE_AD_TENANT_ID = "common"  # Multi-tenant, or specify tenant ID
AZURE_AD_CLIENT_ID = "api://adieuiq"  # Application ID URI


class ManagedIdentityAuth:
    """
    Managed Identity authentication for service-to-service calls.
    Used for Azure SDK clients (Cosmos DB, Redis, Key Vault, etc.)
    """
    
    def __init__(self):
        self.credential = DefaultAzureCredential()
    
    def get_credential(self) -> DefaultAzureCredential:
        """Get Azure credential for SDK clients."""
        return self.credential


class AzureADAuth:
    """
    Azure AD token validation for user authentication.
    Validates JWT tokens from frontend MSAL authentication.
    """
    
    def __init__(self):
        self.jwks_client = PyJWKClient(
            f"https://login.microsoftonline.com/{AZURE_AD_TENANT_ID}/discovery/v2.0/keys"
        )
    
    def validate_token(self, credentials: HTTPAuthorizationCredentials) -> dict:
        """
        Validate Azure AD JWT token and return claims.
        
        Raises:
            HTTPException: If token is invalid or expired
        """
        token = credentials.credentials
        
        try:
            # Get signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Decode and validate token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=AZURE_AD_CLIENT_ID,
                options={"verify_exp": True}
            )
            
            return payload
        
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )


# Global instances
managed_identity = ManagedIdentityAuth()
azure_ad = AzureADAuth()


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    FastAPI dependency for protected endpoints.
    Validates Azure AD token and returns user claims.
    
    Usage:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            user_id = user["oid"]
            user_email = user.get("email")
    """
    return azure_ad.validate_token(credentials)


def check_role(required_role: str):
    """
    Role-based access control dependency.
    Validates user has required role from token claims.
    
    Usage:
        @app.get("/admin")
        async def admin_route(user: dict = Depends(check_role("Administrator"))):
            # Only users with Administrator role can access
    """
    def role_checker(user: dict = Security(get_current_user)) -> dict:
        roles = user.get("roles", [])
        if required_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        return user
    return role_checker
