# Global state for demo
total_requests = 0
total_errors = 0
active_requests = 0

import time
from .main import app, metrics, telemetry


@app.middleware("http")
async def observability_middleware(request, call_next):
    """Middleware to add custom observability"""
    global total_requests, total_errors, active_requests

    start_time = time.time()
    active_requests += 1
    total_requests += 1

    # Update active requests gauge
    metrics["active_requests_gauge"].set(active_requests)

    with telemetry.tracer.start_as_current_span("http_request") as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", str(request.url))

        telemetry.logger.info(f"🚀 {request.method} {request.url.path}")

        response = await call_next(request)
        duration = time.time() - start_time

        # Decrement active requests
        active_requests -= 1
        metrics["active_requests_gauge"].set(active_requests)

        # Record custom metrics
        metrics["request_counter"].add(
            1,
            {
                "method": request.method,
                "endpoint": request.url.path,
                "status_code": str(response.status_code),
            },
        )

        metrics["response_time_histogram"].record(
            duration, {"method": request.method, "endpoint": request.url.path}
        )

        # Track errors
        if response.status_code >= 400:
            total_errors += 1
            telemetry.logger.error(f"❌ Request failed: {response.status_code}")

        # Calculate and update error rate
        error_rate = (total_errors / total_requests) * 100 if total_requests > 0 else 0
        metrics["error_rate_gauge"].set(error_rate)

        span.set_attribute("http.status_code", response.status_code)
        span.set_attribute("http.response_time_ms", duration * 1000)

        telemetry.logger.info(
            f"✅ {request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)"
        )

        return response
