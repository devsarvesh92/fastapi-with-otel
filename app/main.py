# main.py
"""
FastAPI application using Pydantic-based OTEL setup.
"""

import random
import time
from fastapi import FastAPI, HTTPException
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace

# Import our clean OTEL setup with Pydantic
from app.otel_setup import setup_otel_default, create_metrics_instruments

# Initialize OTEL
telemetry = setup_otel_default("fastapi-with-otel")

# Create FastAPI app
app = FastAPI(
    title="FastAPI with Pydantic OTEL Setup",
    description="FastAPI app with Pydantic-based OTEL configuration",
    version="1.0.0",
)

# Auto-instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

# Create metrics instruments
metrics = create_metrics_instruments(telemetry.meter)


@app.get("/")
async def root():
    """Homepage endpoint"""
    with telemetry.tracer.start_as_current_span("homepage") as span:
        span.set_attribute("page.type", "homepage")

        telemetry.logger.info("🏠 Homepage accessed")

        return {
            "message": "FastAPI with Pydantic OTEL Setup!",
            "setup": "Clean, type-safe, and validated",
            "observability": ["metrics", "traces", "logs"],
        }


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get user by ID"""
    with telemetry.tracer.start_as_current_span("get_user") as span:
        span.set_attribute("user.id", user_id)

        # Business metric
        metrics["user_lookups_counter"].add(
            1, {"user_type": "standard" if user_id < 1000 else "premium"}
        )

        telemetry.logger.info(f"👤 Looking up user {user_id}")

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


@app.get("/config")
async def get_config():
    """Show current OTEL configuration"""
    with telemetry.tracer.start_as_current_span("get_config") as span:
        telemetry.logger.info("📋 Configuration requested")

        return {
            "message": "OTEL Configuration",
            "setup_type": "Pydantic-based",
            "components": {
                "tracer": str(type(telemetry.tracer).__name__),
                "meter": str(type(telemetry.meter).__name__),
                "telemetry.logger": str(type(telemetry.logger).__name__),
            },
        }


@app.post("/orders")
async def create_order(order: dict):
    """Create a new order"""
    with telemetry.tracer.start_as_current_span("create_order") as span:
        amount = order.get("amount", 0)
        span.set_attribute("order.amount", amount)

        # Business metric
        metrics["orders_counter"].add(
            1, {"order_size": "large" if amount > 100 else "small", "currency": "USD"}
        )

        telemetry.logger.info(f"📦 Creating order for ${amount}")

        # Simulate order processing with nested spans
        with telemetry.tracer.start_as_current_span("validate_order") as validate_span:
            time.sleep(0.01)
            validate_span.add_event("Order validation completed")

        with telemetry.tracer.start_as_current_span("process_payment") as payment_span:
            payment_span.set_attribute("payment.method", "credit_card")
            time.sleep(0.03)
            payment_span.add_event("Payment processed")

        with telemetry.tracer.start_as_current_span(
            "update_inventory"
        ) as inventory_span:
            time.sleep(0.01)
            inventory_span.add_event("Inventory updated")

        return {
            "order_id": f"order_{int(time.time())}",
            "amount": amount,
            "status": "created",
        }


@app.get("/health")
async def health():
    """Health check endpoint"""
    with telemetry.tracer.start_as_current_span("health_check") as span:
        telemetry.logger.info("❤️ Health check")

        return {
            "status": "healthy",
            "service": "fastapi-clean-demo",
            "observability": "enabled",
        }


@app.get("/metrics-demo")
async def metrics_demo():
    """Generate demo metrics for testing"""
    with telemetry.tracer.start_as_current_span("metrics_demo") as span:

        # Generate some random metrics
        for i in range(5):
            metrics["user_lookups_counter"].add(
                1, {"user_type": random.choice(["standard", "premium"])}
            )

        metrics["orders_counter"].add(
            random.randint(1, 3),
            {"order_size": random.choice(["small", "large"]), "currency": "USD"},
        )

        telemetry.logger.info("📊 Generated demo metrics")

        return {
            "message": "Demo metrics generated!",
            "generated": {"user_lookups": 5, "orders": "1-3 random orders"},
        }


@app.get("/slow")
async def slow_endpoint():
    """Slow endpoint for testing response time metrics"""
    with telemetry.tracer.start_as_current_span("slow_operation") as span:
        telemetry.logger.info("🐌 Starting slow operation")

        # Simulate multiple slow steps
        for i in range(3):
            with telemetry.tracer.start_as_current_span(
                f"slow_step_{i+1}"
            ) as step_span:
                time.sleep(0.7)
                step_span.add_event(f"Completed step {i+1}")
                telemetry.logger.info(f"⏳ Completed slow step {i+1}")

        telemetry.logger.info("✅ Slow operation completed")
        return {"message": "Slow operation completed", "duration": "~2 seconds"}


@app.get("/error")
async def error_endpoint():
    """Error endpoint for testing error metrics"""
    with telemetry.tracer.start_as_current_span("error_operation") as span:
        telemetry.logger.error("💥 Triggering error for metrics testing")
        span.set_status(trace.Status(trace.StatusCode.ERROR, "Demo error"))

        raise HTTPException(status_code=500, detail="Demo error for testing metrics")


@app.get("/random")
async def random_endpoint():
    """Random success/failure endpoint for testing error rates"""
    with telemetry.tracer.start_as_current_span("random_operation") as span:

        success = random.choice([True, True, True, False])  # 75% success rate

        if success:
            telemetry.logger.info("🎲 Random operation succeeded")
            return {"result": "success", "value": random.randint(1, 100)}
        else:
            telemetry.logger.error("🎲 Random operation failed")
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Random failure"))
            raise HTTPException(status_code=500, detail="Random failure")
