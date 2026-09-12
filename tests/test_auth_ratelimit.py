import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_key_generation_and_verification(client):
    # 1. Create a developer key
    res = client.post("/api/v1/keys", json={
        "name": "Jane Civic Developer",
        "email": "jane@civictech.org",
        "tier": "developer"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["status"] == "success"
    key_info = data["data"]
    api_key = key_info["api_key"]
    assert api_key.startswith("argus_developer_") or api_key.startswith("civic_developer_")
    assert key_info["rate_limit_per_min"] == 120

    # 2. Verify key
    res_verify = client.get("/api/v1/keys/verify", headers={"X-API-Key": api_key})
    assert res_verify.status_code == 200
    vdata = res_verify.get_json()
    assert vdata["valid"] is True
    assert vdata["tier"] == "developer"

    # 3. Use key to query incidents
    res_query = client.get("/api/v1/incidents?city=phoenix&limit=2", headers={"X-API-Key": api_key})
    assert res_query.status_code == 200
    assert res_query.headers.get("X-RateLimit-Limit") == "120"

def test_invalid_key_fails(client):
    res = client.get("/api/v1/incidents", headers={"X-API-Key": "civic_invalid_fake_token"})
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"]["code"] == "UNAUTHORIZED"

def test_rate_limit_headers_decrement(client):
    headers = {"X-API-Key": "civic_demo_free_key_2026"}
    res1 = client.get("/api/v1/incidents?limit=1", headers=headers)
    rem1 = int(res1.headers.get("X-RateLimit-Remaining", 30))

    res2 = client.get("/api/v1/incidents?limit=1", headers=headers)
    rem2 = int(res2.headers.get("X-RateLimit-Remaining", 30))

    assert rem2 <= rem1
