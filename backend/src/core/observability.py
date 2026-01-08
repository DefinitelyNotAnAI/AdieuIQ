"""
OpenTelemetry observability setup for distributed tracing.
Constitutional Principle IV: Observability & Monitoring
"""

import logging
from typing import Callable
from fastapi import Request, Response
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentation
from opentelemetry.trace import Status, StatusCode
import uuid


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] %(message)s'
)


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""
    
    def filter(self, record):
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = 'N/A'
        return True


# Add correlation ID filter to root logger
logging.getLogger().addFilter(CorrelationIdFilter())


def setup_observability(app_insights_connection_string: str):
    """
    Initialize OpenTelemetry tracing with Azure Monitor.
    
    Args:
        app_insights_connection_string: Application Insights connection string
    """
    # Create tracer provider
    trace.set_tracer_provider(TracerProvider())
    tracer_provider = trace.get_tracer_provider()
    
    # Configure Azure Monitor exporter
    azure_exporter = AzureMonitorTraceExporter.from_connection_string(
        app_insights_connection_string
    )
    
    # Add span processor
    tracer_provider.add_span_processor(
        BatchSpanProcessor(azure_exporter)
    )
    
    logging.info("✅ OpenTelemetry tracing configured with Azure Monitor")


def instrument_fastapi(app):
    """
    Instrument FastAPI app with OpenTelemetry.
    
    Args:
        app: FastAPI application instance
    """
    FastAPIInstrumentation().instrument_app(app)
    logging.info("✅ FastAPI instrumented with OpenTelemetry")


async def correlation_id_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to add correlation ID to all requests.
    Correlation ID is passed to all downstream services and logged.
    """
    # Get or generate correlation ID
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    
    # Add to request state
    request.state.correlation_id = correlation_id
    
    # Add to current span
    current_span = trace.get_current_span()
    if current_span:
        current_span.set_attribute("correlation_id", correlation_id)
    
    # Process request
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    except Exception as e:
        # Log error with correlation ID
        logging.error(
            f"Request failed: {str(e)}",
            extra={"correlation_id": correlation_id},
            exc_info=True
        )
        
        # Add error to span
        if current_span:
            current_span.set_status(Status(StatusCode.ERROR))
            current_span.record_exception(e)
        
        raise


def get_tracer(name: str) -> trace.Tracer:
    """
    Get OpenTelemetry tracer for service component.
    
    Usage:
        tracer = get_tracer("recommendation_service")
        
        with tracer.start_as_current_span("generate_recommendations"):
            # Your code here
            span = trace.get_current_span()
            span.set_attribute("customer_id", customer_id)
            span.set_attribute("recommendation_count", len(recommendations))
    """
    return trace.get_tracer(name)


def log_with_correlation(
    message: str,
    level: str = "info",
    correlation_id: str = None,
    **kwargs
):
    """
    Log message with correlation ID.
    
    Args:
        message: Log message
        level: Log level (info, warning, error)
        correlation_id: Correlation ID (from request.state.correlation_id)
        **kwargs: Additional context to log
    """
    logger = logging.getLogger(__name__)
    log_func = getattr(logger, level.lower(), logger.info)
    
    extra = {"correlation_id": correlation_id or "N/A"}
    extra.update(kwargs)
    
    log_func(message, extra=extra)
