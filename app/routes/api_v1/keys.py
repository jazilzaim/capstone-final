from flask import request, jsonify
from app.routes.api_v1 import api_v1_bp
from app.models.storage import db
from app.core.exceptions import APIError, UnauthorizedError
from app.core.auth import get_api_key_from_request

@api_v1_bp.route("/keys", methods=["POST"])
@api_v1_bp.route("/keys/generate", methods=["POST"])
def create_key():
    """Self-service API Key generation."""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    tier = data.get("tier", "free").lower().strip()

    if not name or not email:
        raise APIError("Both 'name' and 'email' fields are required to issue an API key.", status_code=400)

    if tier not in ["free", "developer", "enterprise"]:
        tier = "free"

    result = db.create_api_key(name=name, email=email, tier=tier)
    return jsonify({
        "status": "success",
        "message": "API key generated successfully. Save this key securely, it will not be shown again in full.",
        "data": result
    }), 201

@api_v1_bp.route("/keys/verify", methods=["GET"])
def verify_key():
    """Verify an API key and check remaining rate limit quota."""
    api_key = get_api_key_from_request()
    if not api_key:
        raise UnauthorizedError("No API key provided. Pass via 'X-API-Key' header or '?api_key=' parameter.")

    info = db.get_key_info(api_key)
    if not info:
        raise UnauthorizedError("Invalid or inactive API key.")

    return jsonify({
        "status": "success",
        "valid": True,
        "key_prefix": info.get("key_prefix", ""),
        "name": info.get("name", ""),
        "tier": info.get("tier", "free"),
        "total_requests": info.get("total_requests", 0),
        "created_at": info.get("created_at") or ""
    })
