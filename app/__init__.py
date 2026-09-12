import time
import secrets
from flask import Flask, session, request, g
from app.config import Config
from app.core.exceptions import register_error_handlers
from app.routes.api_v1 import api_v1_bp
from app.routes.web.views import web_bp

def create_app(config_class=Config) -> Flask:
    """Application factory for Argus API product."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register error handlers
    register_error_handlers(app)

    # Register Blueprints
    app.register_blueprint(api_v1_bp)
    app.register_blueprint(web_bp)

    @app.before_request
    def assign_request_context():
        """Assign unique request ID and capture high-resolution request start time."""
        g.request_id = request.headers.get("X-Request-Id") or f"req_{secrets.token_hex(6)}"
        g.start_time = time.time()

    @app.context_processor
    def inject_auth_user():
        """Make current authenticated user and primary API key available across all templates."""
        user = session.get("user")
        primary_key = None
        user_tier = "free"
        if user and user.get("email"):
            from app.models.storage import db
            keys = db.get_user_keys(user["email"])
            if keys and len(keys) > 0:
                primary_key = keys[0]["key_hash"]
                user_tier = keys[0].get("tier", "free")
        return dict(
            current_user=user,
            user_primary_key=primary_key or "argus_demo_free_key_2026",
            user_primary_key_masked=(primary_key[:16] + "••••••••") if primary_key else "argus_demo_free_••••",
            user_plan_tier=user_tier
        )

    @app.after_request
    def set_security_and_observability_headers(response):
        """Production security headers, CORS, and request tracing metadata."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-API-Key, Authorization, X-Request-Id"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"

        if hasattr(g, "request_id"):
            response.headers["X-Request-Id"] = g.request_id

        if hasattr(g, "is_cached"):
            response.headers["X-Cache"] = "HIT" if g.is_cached else "MISS"

        return response

    return app
