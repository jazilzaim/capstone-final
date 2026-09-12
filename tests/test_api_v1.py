import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_cities_endpoint(client):
    res = client.get("/api/v1/cities")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["total_cities"] == 4
    city_ids = [c["city_id"] for c in data["data"]]
    assert "las_vegas" in city_ids
    assert "los_angeles" in city_ids
    assert "seattle" in city_ids
    assert "phoenix" in city_ids

def test_incidents_without_api_key_fails(client):
    res = client.get("/api/v1/incidents")
    assert res.status_code == 401
    data = res.get_json()
    assert data["status"] == "error"
    assert data["error"]["code"] == "UNAUTHORIZED"

def test_incidents_with_demo_key(client):
    headers = {"X-API-Key": "civic_demo_free_key_2026"}
    res = client.get("/api/v1/incidents?city=los_angeles&limit=3", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert len(data["data"]) > 0
    assert data["meta"]["city"] == "los_angeles"
    assert "X-RateLimit-Limit" in res.headers
    assert "X-RateLimit-Remaining" in res.headers

def test_cross_city_incidents(client):
    headers = {"X-API-Key": "civic_demo_free_key_2026"}
    res = client.get("/api/v1/incidents?city=all&limit=8", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert len(data["data"]) > 0

def test_permits_endpoint(client):
    headers = {"X-API-Key": "civic_demo_free_key_2026"}
    res = client.get("/api/v1/permits?city=seattle&limit=2", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert len(data["data"]) > 0

def test_businesses_endpoint(client):
    headers = {"X-API-Key": "civic_demo_free_key_2026"}
    res = client.get("/api/v1/businesses?city=las_vegas&limit=2", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert len(data["data"]) > 0

def test_analytics_summary(client):
    headers = {"X-API-Key": "civic_demo_free_key_2026"}
    res = client.get("/api/v1/analytics/summary", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "breakdown_by_category" in data["data"]
    assert "construction_pipeline" in data["data"]

def test_health_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert "cache" in data
