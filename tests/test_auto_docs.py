import pytest
from app import create_app
from app.models.storage import db

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key-for-docs"
    with app.test_client() as client:
        yield client

def test_unauthenticated_docs_has_generic_key_and_tip(client):
    res = client.get("/docs")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Argus API Reference" in html
    assert "Sign in" in html or "login" in html
    assert "argus_demo_free_key_2026" in html

def test_authenticated_user_has_personalized_docs_and_keys(client):
    # Log in as demo user
    login_res = client.post("/login", data={
        "email": "developer@argus.dev",
        "password": "Password123!"
    }, follow_redirects=True)
    assert login_res.status_code == 200

    # Retrieve user's key from storage to assert exact match
    user = db.get_user_by_email("developer@argus.dev")
    assert user is not None
    user_keys = db.get_user_keys(user["email"])
    assert len(user_keys) > 0
    primary_key = user_keys[0].get("key_hash") or user_keys[0].get("key")
    assert primary_key is not None

    # 1. Check /dashboard contains auto-generated quickstart with user's key
    dash_res = client.get("/dashboard")
    assert dash_res.status_code == 200
    dash_html = dash_res.get_data(as_text=True)
    assert "Auto-Generated API Quickstart" in dash_html
    assert primary_key in dash_html
    assert "Personalized for" in dash_html

    # 2. Check /docs contains personalized header and injected API key
    docs_res = client.get("/docs")
    assert docs_res.status_code == 200
    docs_html = docs_res.get_data(as_text=True)
    assert f"Personalized for {user['name']}" in docs_html
    assert primary_key in docs_html
    assert "Live API credentials automatically injected" in docs_html

    # 3. Check /dashboard/workbench pre-fills user's active key
    wb_res = client.get("/dashboard/workbench")
    assert wb_res.status_code == 200
    wb_html = wb_res.get_data(as_text=True)
    assert f'value="{primary_key}"' in wb_html

    # 4. Check /playground pre-fills user's active key
    pg_res = client.get("/playground")
    assert pg_res.status_code == 200
    pg_html = pg_res.get_data(as_text=True)
    assert f'value="{primary_key}"' in pg_html
    assert f"Personal Key ({user['name']})" in pg_html
