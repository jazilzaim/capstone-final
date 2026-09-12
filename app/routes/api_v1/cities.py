from flask import jsonify
from app.routes.api_v1 import api_v1_bp
from app.connectors.registry import registry
from app.core.exceptions import NotFoundError
from app.core.cache import cache
from app.models.storage import db

@api_v1_bp.route("/cities", methods=["GET"])
def get_cities():
    """List all supported municipal portals, connector health, and latency."""
    cities_info = [c.to_dict() for c in registry.get_all_cities_info()]
    return jsonify({
        "status": "success",
        "total_cities": len(cities_info),
        "data": cities_info
    })

@api_v1_bp.route("/cities/<city_id>", methods=["GET"])
def get_city_detail(city_id: str):
    """Retrieve details, datasets, and operational health of a single city."""
    connector = registry.get_connector(city_id)
    if not connector:
        raise NotFoundError(f"City '{city_id}' is not supported. Supported cities: {registry.list_city_ids()}")

    return jsonify({
        "status": "success",
        "data": connector.get_info().to_dict()
    })

@api_v1_bp.route("/health", methods=["GET"])
def health_check():
    """System health check and caching performance telemetry."""
    cache_stats = cache.stats()
    system_stats = db.get_system_stats()
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "service": "Argus API",
        "cache": cache_stats,
        "metrics": system_stats
    })
