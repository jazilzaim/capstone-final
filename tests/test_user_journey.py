import secrets
import pytest
from app import create_app
from app.models.storage import db

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key-for-journey"
    with app.test_client() as client:
        yield client

def test_complete_end_to_end_developer_journey(client):
    """
    End-to-End User Test:
    1. Sign up new developer
    2. Verify auto-generated credentials and tier
    3. Verify personalized dashboard quickstart and auto-docs
    4. Verify workbench and playground key pre-fills
    5. Execute API queries across all 4 cities with user key
    6. Verify rate limit header decrements
    7. Generate a secondary key
    8. Sign out and verify route protection
    """
    token = secrets.token_hex(4)
    dev_name = f"Alex Rivera {token}"
    dev_email = f"alex_{token}@acmedata.io"
    password = "SecureDevPass2026!"

    # --- 1. Sign Up ---
    signup_res = client.post("/signup", data={
        "name": dev_name,
        "email": dev_email,
        "password": password
    }, follow_redirects=False)
    assert signup_res.status_code == 302
    assert "/dashboard" in signup_res.headers["Location"]

    # Verify user in database and primary key provisioned
    user = db.get_user_by_email(dev_email)
    assert user is not None
    assert user["name"] == dev_name

    user_keys = db.get_user_keys(dev_email)
    assert len(user_keys) >= 1
    primary_key = user_keys[0]["key_hash"]
    assert primary_key.startswith("argus_")

    # --- 2. Dashboard Overview Verification ---
    dash_res = client.get("/dashboard")
    assert dash_res.status_code == 200
    dash_html = dash_res.get_data(as_text=True)
    assert "Auto-Generated API Quickstart" in dash_html
    assert primary_key in dash_html
    assert dev_name in dash_html
    assert "X-Request-Id" in dash_res.headers
    assert dash_res.headers.get("X-Content-Type-Options") == "nosniff"

    # --- 3. Interactive Documentation Verification ---
    docs_res = client.get("/docs")
    assert docs_res.status_code == 200
    docs_html = docs_res.get_data(as_text=True)
    assert f"Personalized for {dev_name}" in docs_html
    assert primary_key in docs_html
    assert "Live API credentials automatically injected" in docs_html

    # --- 4. Workbench & Playground Pre-Fill ---
    wb_res = client.get("/dashboard/workbench")
    assert wb_res.status_code == 200
    assert f'value="{primary_key}"' in wb_res.get_data(as_text=True)

    pg_res = client.get("/playground")
    assert pg_res.status_code == 200
    assert f'value="{primary_key}"' in pg_res.get_data(as_text=True)

    # --- 5. Execute API Queries across All 4 Municipalities ---
    headers = {"X-API-Key": primary_key}

    # City 1: Las Vegas
    lv_res = client.get("/api/v1/incidents?city=las_vegas&limit=3", headers=headers)
    assert lv_res.status_code == 200
    lv_data = lv_res.get_json()
    assert lv_data["status"] == "success"
    assert lv_data["meta"]["city"] == "las_vegas"

    # City 2: Los Angeles
    la_res = client.get("/api/v1/permits?city=los_angeles&limit=3", headers=headers)
    assert la_res.status_code == 200
    la_data = la_res.get_json()
    assert la_data["status"] == "success"
    assert la_data["meta"]["city"] == "los_angeles"

    # City 3: Seattle
    sea_res = client.get("/api/v1/businesses?city=seattle&limit=3", headers=headers)
    assert sea_res.status_code == 200
    sea_data = sea_res.get_json()
    assert sea_data["status"] == "success"
    assert sea_data["meta"]["city"] == "seattle"

    # City 4: Phoenix
    phx_res = client.get("/api/v1/incidents?city=phoenix&limit=3", headers=headers)
    assert phx_res.status_code == 200
    phx_data = phx_res.get_json()
    assert phx_data["status"] == "success"
    assert phx_data["meta"]["city"] == "phoenix"

    # Cross-City Parallel Aggregate
    all_res = client.get("/api/v1/incidents?city=all&limit=8", headers=headers)
    assert all_res.status_code == 200
    all_data = all_res.get_json()
    assert all_data["status"] == "success"
    assert all_data["meta"]["city"] == "all"
    assert len(all_data["data"]) > 0

    # --- 6. Rate Limiting Verification ---
    rem_header = all_res.headers.get("X-RateLimit-Remaining")
    assert rem_header is not None
    assert int(rem_header) < 30  # Decremented from initial 30 limit

    # --- 7. Generate Secondary API Key ---
    gen_res = client.post("/api/v1/keys/generate", json={
        "name": "Production Webhook Service",
        "email": dev_email,
        "tier": "developer"
    })
    assert gen_res.status_code == 201
    gen_data = gen_res.get_json()
    assert "data" in gen_data
    second_key = gen_data["data"]["api_key"]
    assert second_key.startswith("argus_")

    # Verify user now has 2 keys
    updated_keys = db.get_user_keys(dev_email)
    assert len(updated_keys) >= 2

    # --- 8. Sign Out & Route Protection ---
    logout_res = client.get("/logout", follow_redirects=False)
    assert logout_res.status_code == 302

    # Attempt accessing dashboard as guest
    guest_res = client.get("/dashboard")
    assert guest_res.status_code == 302
    assert "/login" in guest_res.headers["Location"]
