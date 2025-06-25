"""OTEL Setup with Pydantic"""

from pydantic import BaseModel
import logging
from opentelemetry import trace, metrics
from opentelemetry.trace import Tracer
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.metrics import Meter

# OTLP Exporters
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

# Logging setup
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry._logs import set_logger_provider


class OTELConfig(BaseModel):
    service_name: str = "fastapi-service"
    service_version: str = "1.0.0"
    service_instance_id: str = "instance-1"
    environment: str = "development"
    collector_endpoint: str = "http://localhost:4317"
    metric_export_interval_ms: int = 5000


class Telemetry(BaseModel):
    """Telemetry objects for the application"""

    tracer: Tracer
    meter: Meter
    logger: logging.Logger

    class Config:
        arbitrary_types_allowed = True  # Allow non-Pydantic types


def setup_otel(config: OTELConfig) -> Telemetry:
    """
    Setup OpenTelemetry with traces, metrics, and logs.

    Args:
        config: OTELConfig object with configuration parameters

    Returns:
        Telemetry: Object containing tracer, meter, and logger
    """
    print("🏗️ Setting up OpenTelemetry...")

    # Create resource that identifies the service
    resource = Resource.create(
        {
            "service.name": config.service_name,
            "service.version": config.service_version,
            "service.instance.id": config.service_instance_id,
            "deployment.environment": config.environment,
        }
    )

    # Setup traces
    tracer: Tracer = _setup_tracing(resource, config.collector_endpoint)

    # Setup metrics
    meter = _setup_metrics(
        resource, config.collector_endpoint, config.metric_export_interval_ms
    )

    # Setup logs
    logger = _setup_logging(resource, config.collector_endpoint)

    print("✅ OpenTelemetry setup completed!")
    print(f"📊 Metrics: {config.service_name} → OTEL Collector → Prometheus")
    print(f"🔍 Traces: {config.service_name} → OTEL Collector → Tempo")
    print(f"📝 Logs: {config.service_name} → OTEL Collector → Loki")

    return Telemetry(tracer=tracer, meter=meter, logger=logger)


def _setup_tracing(resource: Resource, collector_endpoint: str) -> Tracer:
    """Setup distributed tracing"""
    print("🔍 Configuring traces...")

    # Create tracer provider - FIXED: Don't create duplicate providers
    trace_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(trace_provider)  # Use the same provider instance

    # Get tracer from the provider
    tracer = trace.get_tracer(__name__)

    # OTLP span exporter
    otlp_span_exporter = OTLPSpanExporter(endpoint=collector_endpoint, insecure=True)

    # Batch span processor for efficiency
    span_processor = BatchSpanProcessor(otlp_span_exporter)
    trace_provider.add_span_processor(span_processor)  # Add to the same provider

    return tracer


def _setup_metrics(
    resource: Resource, collector_endpoint: str, export_interval_ms: int
) -> Meter:
    """Setup metrics collection"""
    print("📊 Configuring metrics...")

    # OTLP metric exporter
    otlp_metric_exporter = OTLPMetricExporter(
        endpoint=collector_endpoint, insecure=True
    )

    # Periodic metric reader
    metric_reader = PeriodicExportingMetricReader(
        exporter=otlp_metric_exporter, export_interval_millis=export_interval_ms
    )

    # Set meter provider
    metrics.set_meter_provider(
        MeterProvider(resource=resource, metric_readers=[metric_reader])
    )

    meter = metrics.get_meter(__name__)
    return meter


def _setup_logging(resource: Resource, collector_endpoint: str) -> logging.Logger:
    """Setup structured logging"""
    print("📝 Configuring logs...")

    # Create logger provider
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)

    # OTLP log exporter
    otlp_log_exporter = OTLPLogExporter(endpoint=collector_endpoint, insecure=True)

    # Batch log processor
    log_processor = BatchLogRecordProcessor(otlp_log_exporter)
    logger_provider.add_log_record_processor(log_processor)

    # Configure Python logging
    logging_handler = LoggingHandler(
        level=logging.INFO, logger_provider=logger_provider
    )

    # Setup logging with both OTEL and console output
    logging.basicConfig(
        level=logging.INFO,
        handlers=[logging_handler, logging.StreamHandler()],
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger(__name__)
    return logger


def create_metrics_instruments(meter: Meter) -> dict:
    """Create common metrics instruments for FastAPI"""
    return {
        "request_counter": meter.create_counter(
            name="http_requests_custom_total",
            description="Total HTTP requests (custom counter)",
        ),
        "response_time_histogram": meter.create_histogram(
            name="http_request_duration_seconds",
            description="HTTP request duration in seconds",
            unit="s",
        ),
        "orders_counter": meter.create_counter(
            name="orders_created_total", description="Total orders created"
        ),
        "user_lookups_counter": meter.create_counter(
            name="user_lookups_total", description="Total user lookups performed"
        ),
        "active_requests_gauge": meter.create_gauge(
            name="active_requests_current", description="Currently active HTTP requests"
        ),
        "error_rate_gauge": meter.create_gauge(
            name="error_rate_current", description="Current error rate percentage"
        ),
    }


# Convenience function for default setup
def setup_otel_default(service_name: str = "fastapi-service") -> Telemetry:
    """Setup OTEL with default configuration"""
    config = OTELConfig(service_name=service_name)
    return setup_otel(config)
