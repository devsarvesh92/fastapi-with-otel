import logging
import random
import time
from fastapi import FastAPI, HTTPException
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# OTLP Exporter for metrics (to collector)
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter


# Console for traces/logs (for now)
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry._logs import set_logger_provider

app = FastAPI(title="FastAPI with Prometheus via Collector")

print("🏗️ Setting up FastAPI with OTEL Collector for Metrics...")

# Resource identifies your service
resource = Resource.create(
    {
        "service.name": "fastapi-prometheus-demo",
        "service.version": "1.0.0",
        "service.instance.id": "instance-1",
        "deployment.environment": "development",
    }
)

# TRACES: Keep console for now (will upgrade later)
print("🔍 Setting up TRACES → Console (for now)...")
trace_provider = TracerProvider(resource=resource)

trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer(__name__)

console_span_exporter = ConsoleSpanExporter()
span_processor = BatchSpanProcessor(console_span_exporter)
trace_provider.add_span_processor(span_processor)

# METRICS: OTLP to Collector → Prometheus
print("📊 Setting up METRICS → Collector → Prometheus...")
otlp_metric_exporter = OTLPMetricExporter(
    endpoint="http://localhost:4317", insecure=True  # OTEL Collector
)
metric_reader = PeriodicExportingMetricReader(
    exporter=otlp_metric_exporter, export_interval_millis=5000  # Export every 5 seconds
)
metrics.set_meter_provider(
    MeterProvider(resource=resource, metric_readers=[metric_reader])
)

# LOGS: Keep console for now (will upgrade later)
print("📝 Setting up LOGS → Console (for now)...")
logger_provider = LoggerProvider(resource=resource)
set_logger_provider(logger_provider)

console_log_exporter = ConsoleLogExporter()
log_processor = BatchLogRecordProcessor(console_log_exporter)
logger_provider.add_log_record_processor(log_processor)

# Configure Python logging
logging_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
logging.basicConfig(
    level=logging.INFO, handlers=[logging_handler, logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Auto-instrument FastAPI (gives automatic HTTP metrics)
FastAPIInstrumentor.instrument_app(app)

# Create custom metrics
meter = metrics.get_meter(__name__)

# HTTP Request metrics
custom_request_counter = meter.create_counter(
    name="http_requests_custom_total",
    description="Total HTTP requests (custom counter)",
)

response_time_histogram = meter.create_histogram(
    name="http_request_duration_seconds",
    description="HTTP request duration in seconds",
    unit="s",
)

# Business metrics
orders_counter = meter.create_counter(
    name="orders_created_total", description="Total orders created"
)

user_lookups_counter = meter.create_counter(
    name="user_lookups_total", description="Total user lookups performed"
)

# System metrics
active_requests_gauge = meter.create_gauge(
    name="active_requests_current", description="Currently active HTTP requests"
)

error_rate_gauge = meter.create_gauge(
    name="error_rate_current", description="Current error rate percentage"
)

# Global counters for demo
total_requests = 0
total_errors = 0
active_requests = 0


@app.middleware("http")
async def metrics_middleware(request, call_next):
    global total_requests, total_errors, active_requests

    start_time = time.time()
    active_requests += 1
    total_requests += 1

    # Update active requests gauge
    active_requests_gauge.set(active_requests)

    with tracer.start_as_current_span("http_request") as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", str(request.url))

        logger.info(f"🚀 {request.method} {request.url.path}")

        response = await call_next(request)
        duration = time.time() - start_time

        # Decrement active requests
        active_requests -= 1
        active_requests_gauge.set(active_requests)

        # Record custom metrics
        custom_request_counter.add(
            1,
            {
                "method": request.method,
                "endpoint": request.url.path,
                "status_code": str(response.status_code),
            },
        )

        response_time_histogram.record(
            duration, {"method": request.method, "endpoint": request.url.path}
        )

        # Track errors
        if response.status_code >= 400:
            total_errors += 1
            logger.error(f"❌ Request failed: {response.status_code}")

        # Calculate and update error rate
        error_rate = (total_errors / total_requests) * 100 if total_requests > 0 else 0
        error_rate_gauge.set(error_rate)

        span.set_attribute("http.status_code", response.status_code)
        span.set_attribute("http.response_time_ms", duration * 1000)

        logger.info(
            f"✅ {request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)"
        )

        return response


@app.get("/")
async def root():
    with tracer.start_as_current_span("homepage") as span:
        span.set_attribute("page.type", "homepage")

        logger.info("🏠 Homepage accessed")

        return {
            "message": "FastAPI with Prometheus Metrics!",
            "metrics_flow": "FastAPI → OTEL Collector → Prometheus → Grafana",
            "endpoints": ["/", "/users/{id}", "/orders", "/health", "/metrics-demo"],
        }


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    with tracer.start_as_current_span("get_user") as span:
        span.set_attribute("user.id", user_id)

        # Business metric
        user_lookups_counter.add(
            1, {"user_type": "standard" if user_id < 1000 else "premium"}
        )

        logger.info(f"👤 Looking up user {user_id}")

        # Simulate some processing time
        time.sleep(0.02)

        if user_id <= 0:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid user ID"))
            raise HTTPException(status_code=400, detail="User ID must be positive")

        return {
            "user_id": user_id,
            "name": f"User {user_id}",
            "type": "premium" if user_id >= 1000 else "standard",
        }


@app.post("/orders")
async def create_order(order: dict):
    with tracer.start_as_current_span("create_order") as span:
        amount = order.get("amount", 0)
        span.set_attribute("order.amount", amount)

        # Business metric
        orders_counter.add(
            1, {"order_size": "large" if amount > 100 else "small", "currency": "USD"}
        )

        logger.info(f"📦 Creating order for ${amount}")

        # Simulate order processing
        time.sleep(0.05)

        return {
            "order_id": f"order_{int(time.time())}",
            "amount": amount,
            "status": "created",
        }


@app.get("/health")
async def health():
    with tracer.start_as_current_span("health_check") as span:
        logger.info("❤️ Health check")

        return {
            "status": "healthy",
            "service": "fastapi-prometheus-demo",
            "metrics": "enabled",
        }


@app.get("/metrics-demo")
async def metrics_demo():
    """Endpoint to generate various metrics for testing"""
    currencies = ["USD", "INR", "CNF", "CKD", "DUMMY"]
    with tracer.start_as_current_span("metrics_demo") as span:

        # Generate some random metrics
        for i in range(5):
            user_lookups_counter.add(
                1, {"user_type": random.choice(["standard", "premium"])}
            )

        orders_counter.add(
            random.randint(1, 3),
            {
                "order_size": random.choice(["small", "large"]),
                "currency": currencies[2],
            },
        )

        logger.info("📊 Generated demo metrics")

        return {
            "message": "Demo metrics generated!",
            "generated": {"user_lookups": 5, "orders": "1-3 random orders"},
        }


@app.get("/slow")
async def slow_endpoint():
    with tracer.start_as_current_span("slow_operation") as span:
        logger.info("🐌 Starting slow operation")

        # This will show up nicely in response time metrics
        time.sleep(2)

        logger.info("✅ Slow operation completed")
        return {"message": "Slow operation completed", "duration": "2 seconds"}


@app.get("/error")
async def error_endpoint():
    with tracer.start_as_current_span("error_operation") as span:
        logger.error("💥 Triggering error for metrics testing")
        span.set_status(trace.Status(trace.StatusCode.ERROR, "Demo error"))

        raise HTTPException(status_code=500, detail="Demo error for testing metrics")


@app.get("/random")
async def random_endpoint():
    """Endpoint that randomly succeeds or fails - good for error rate metrics"""
    with tracer.start_as_current_span("random_operation") as span:

        success = random.choice([True, True, True, False])  # 75% success rate

        if success:
            logger.info("🎲 Random operation succeeded")
            return {"result": "success", "value": random.randint(1, 100)}
        else:
            logger.error("🎲 Random operation failed")
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Random failure"))
            raise HTTPException(status_code=500, detail="Random failure")
