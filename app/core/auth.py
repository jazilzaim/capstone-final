from functools import wraps
from typing import Optional, Dict, Any
from flask import request, g, session, redirect, url_for, flash
from app.models.storage import db
from app.core.exceptions import UnauthorizedError, ForbiddenError

def get_current_user() -> Optional[Dict[str, Any]]:
    """Retrieve currently authenticated user from Flask session."""
    return session.get("user")

def login_required(f):
    """
    Decorator for web routes to require an active user session.
    Redirects unauthenticated visitors to /login with next redirection parameter.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user"):
            next_url = request.full_path if request.query_string else request.path
            flash("Please sign in to access the developer dashboard.", "info")
            return redirect(url_for("web.login", next=next_url))
        return f(*args, **kwargs)
    return decorated_function


def get_api_key_from_request() -> str:
    """Extract API key from header or query param."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header.replace("Bearer ", "").strip()
    if not api_key:
        api_key = request.args.get("api_key", "").strip()
    return api_key

def require_api_key(required_tier: str = "free"):
    """
    Decorator for API endpoints to require valid API key and check tier eligibility.
    Tier hierarchy: free (lowest) < developer < enterprise (highest).
    """
    tier_levels = {
        "free": 1,
        "developer": 2,
        "enterprise": 3,
        "internal": 99
    }

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = get_api_key_from_request()
            if not api_key:
                raise UnauthorizedError(
                    message="Missing API key. Provide via 'X-API-Key' header or '?api_key=' parameter. "
                            "You can generate a free key at /keys or use demo key 'argus_demo_free_key_2026'."
                )

            key_info = db.get_key_info(api_key)
            if not key_info:
                raise UnauthorizedError(message="Invalid or revoked API key.")

            user_tier = key_info.get("tier", "free")
            if tier_levels.get(user_tier, 1) < tier_levels.get(required_tier, 1):
                raise ForbiddenError(
                    message=f"This feature requires a '{required_tier}' tier API key. Your key is '{user_tier}' tier."
                )

            # Store key info in Flask g for rate limiting & logging
            g.api_key_info = key_info
            g.api_key = api_key
            return f(*args, **kwargs)
        return decorated_function
    return decorator
