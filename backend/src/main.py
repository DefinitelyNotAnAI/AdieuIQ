"""
FastAPI application entry point for Customer Recommendation Engine.
Constitutional compliance: Security, Observability, CORS, Health checks
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from src.core.config import initialize_secrets, get_settings
from src.core.observability import (
    setup_observability,
    instrument_fastapi,
    correlation_id_middleware
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management.
    Initialize resources on startup, cleanup on shutdown.
    """
    settings = get_settings()
    
    # Startup
    logging.info("🚀 Starting Customer Recommendation Engine API")
    
    # Initialize Key Vault secrets
    try:
        initialize_secrets()
        logging.info("✅ Key Vault secrets initialized")
    except Exception as e:
        logging.error(f"❌ Failed to initialize secrets: {e}")
        # In dev mode, continue without secrets for local testing
        if settings.environment != "dev":
            raise
    
    # Initialize observability
    setup_observability(settings.applicationinsights_connection_string)
    
    logging.info("✅ API startup complete")
    
    yield
    
    # Shutdown
    logging.info("👋 Shutting down Customer Recommendation Engine API")


# Create FastAPI application
app = FastAPI(
    title="Customer Recommendation Engine API",
    description="Azure-native API for personalized customer recommendations",
    version="1.0.0",
    lifespan=lifespan
)

# Get settings
settings = get_settings()

# Add response compression (T069 - compress responses >1KB)
app.add_middleware(
    GZipMiddleware,
    minimum_size=1024,  # Compress responses larger than 1KB
    compresslevel=6  # Balance between speed and compression ratio
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add correlation ID middleware
app.middleware("http")(correlation_id_middleware)

# Instrument with OpenTelemetry
instrument_fastapi(app)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    Returns service status and version.
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "Customer Recommendation Engine API",
            "version": "1.0.0",
            "environment": settings.environment
        }
    )


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Customer Recommendation Engine API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# API route registration
from src.api import customers, recommendations, history

app.include_router(customers.router, prefix="/api/v1")
app.include_router(recommendations.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level="info"
    )
