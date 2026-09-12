import time
from flask import Blueprint, request, g
from app.core.ratelimit import apply_rate_limit
from app.models.storage import db

api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")

@api_v1_bp.before_request
def before_api_request():
    g.start_time = time.time()
    # Apply rate limiting across all /api/v1 endpoints except health/keys creation
    if not request.path.endswith("/keys") and not request.path.endswith("/keys/generate") and not request.path.endswith("/health"):
        apply_rate_limit()

@api_v1_bp.after_request
def after_api_request(response):
    # Inject rate limit headers if present
    rate_headers = getattr(g, "rate_limit_headers", None)
    if rate_headers:
        for k, v in rate_headers.items():
            response.headers[k] = v

    # Inject latency header
    start_time = getattr(g, "start_time", None)
    if start_time:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Response-Time-Ms"] = str(duration_ms)

        # Log usage in storage
        key_info = getattr(g, "api_key_info", None)
        key_prefix = key_info["key_prefix"] if key_info else None
        city = request.args.get("city")
        req_id = f"req_{int(time.time()*1000)%10000000:07d}"
        response.headers["X-Request-Id"] = req_id
        db.record_usage(
            key_prefix=key_prefix,
            endpoint=request.path,
            city=city,
            status_code=response.status_code,
            latency_ms=duration_ms,
            method=request.method,
            query_params=request.query_string.decode("utf-8", errors="ignore"),
            request_id=req_id
        )

    return response

# Import endpoint submodules to register routes
from app.routes.api_v1 import incidents, permits, businesses, cities, analytics, keys, jobs, gov
