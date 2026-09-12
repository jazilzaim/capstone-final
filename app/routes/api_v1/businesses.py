import time
from flask import request, jsonify, g
from app.routes.api_v1 import api_v1_bp
from app.core.auth import require_api_key
from app.core.cache import cache
from app.connectors.registry import registry
from app.core.exceptions import APIError

@api_v1_bp.route("/businesses", methods=["GET"])
@require_api_key(required_tier="free")
def get_businesses():
    """
    Query normalized commercial entities and active business licenses.
    ---
    Query Parameters:
      - city (str): 'los_angeles', 'seattle', 'las_vegas', 'phoenix', or 'all'
      - query (str): Search business name or category
      - limit (int): Max records (1-100, default: 20)
      - offset (int): Pagination offset
    """
    city = request.args.get("city", "all").lower().strip()
    query = request.args.get("query")
    try:
        limit = min(100, max(1, int(request.args.get("limit", 20))))
        offset = max(0, int(request.args.get("offset", 0)))
    except ValueError:
        raise APIError("Invalid 'limit' or 'offset' parameter. Must be integers.", status_code=400)

    cache_key = cache._make_key("businesses", city=city, q=query, lim=limit, off=offset)
    cached_data = cache.get(cache_key)

    is_cached = False
    if cached_data is not None:
        businesses = cached_data
        is_cached = True
    else:
        raw_biz = registry.query_businesses(
            city=city,
            limit=limit,
            offset=offset,
            query=query
        )
        businesses = [b.to_dict() for b in raw_biz]
        cache.set(cache_key, businesses)

    g.is_cached = is_cached
    duration_ms = round((time.time() - getattr(g, "start_time", time.time())) * 1000, 1)

    return jsonify({
        "status": "success",
        "meta": {
            "total": len(businesses),
            "limit": limit,
            "offset": offset,
            "city": city,
            "cached": is_cached,
            "response_time_ms": duration_ms
        },
        "data": businesses
    })
