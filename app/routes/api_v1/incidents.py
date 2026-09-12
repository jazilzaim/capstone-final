import time
from flask import request, jsonify, g
from app.routes.api_v1 import api_v1_bp
from app.core.auth import require_api_key
from app.core.cache import cache
from app.connectors.registry import registry
from app.core.exceptions import APIError

@api_v1_bp.route("/incidents", methods=["GET"])
@require_api_key(required_tier="free")
def get_incidents():
    """
    Query normalized public safety and emergency incidents across Las Vegas, LA, Seattle, and Phoenix.
    ---
    Query Parameters:
      - city (str): 'los_angeles', 'seattle', 'las_vegas', 'phoenix', or 'all' (default: 'all')
      - category (str): e.g. 'Violent Crime', 'Property Crime', 'Traffic'
      - query (str): Text search term
      - limit (int): Max records (1-100, default: 20)
      - offset (int): Pagination offset (default: 0)
    """
    city = request.args.get("city", "all").lower().strip()
    category = request.args.get("category")
    query = request.args.get("query")
    try:
        limit = min(100, max(1, int(request.args.get("limit", 20))))
        offset = max(0, int(request.args.get("offset", 0)))
    except ValueError:
        raise APIError("Invalid 'limit' or 'offset' parameter. Must be integers.", status_code=400)

    # Check cache
    cache_key = cache._make_key("incidents", city=city, category=category, q=query, lim=limit, off=offset)
    cached_data = cache.get(cache_key)

    is_cached = False
    if cached_data is not None:
        incidents = cached_data
        is_cached = True
    else:
        # Fetch from connectors
        raw_incidents = registry.query_incidents(
            city=city,
            limit=limit,
            offset=offset,
            query=query,
            category=category
        )
        incidents = [inc.to_dict() for inc in raw_incidents]
        cache.set(cache_key, incidents)

    g.is_cached = is_cached
    duration_ms = round((time.time() - getattr(g, "start_time", time.time())) * 1000, 1)

    return jsonify({
        "status": "success",
        "meta": {
            "total": len(incidents),
            "limit": limit,
            "offset": offset,
            "city": city,
            "cached": is_cached,
            "response_time_ms": duration_ms
        },
        "data": incidents
    })
