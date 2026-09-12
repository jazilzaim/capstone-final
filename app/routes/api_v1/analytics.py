from flask import jsonify
from app.routes.api_v1 import api_v1_bp
from app.core.auth import require_api_key
from app.connectors.registry import registry
from app.core.cache import cache

@api_v1_bp.route("/analytics/summary", methods=["GET"])
@require_api_key(required_tier="free")
def get_analytics():
    """Retrieve high-level cross-city comparative analytics and statistics."""
    cache_key = "analytics:summary"
    cached = cache.get(cache_key)
    if cached is not None:
        return jsonify({
            "status": "success",
            "cached": True,
            "data": cached
        })

    data = registry.get_analytics_summary()
    cache.set(cache_key, data, ttl=600)  # cache 10 minutes

    return jsonify({
        "status": "success",
        "cached": False,
        "data": data
    })
