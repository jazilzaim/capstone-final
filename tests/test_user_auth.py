import pytest
import secrets
from app import create_app
from app.models.storage import db

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key-for-auth"
    with app.test_client() as client:
        yield client

def test_login_page_renders(client):
    res = client.get("/login")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Sign in to Argus" in html
    assert "Instant Test Account" in html
    assert 'name="email"' in html
    assert 'name="password"' in html

def test_signup_page_renders(client):
    res = client.get("/signup")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Create developer account" in html
    assert "Automatic Sandbox Provisioning" in html
    assert 'name="name"' in html
    assert 'name="email"' in html
    assert 'name="password"' in html

def test_unauthenticated_dashboard_redirect(client):
    # Accessing dashboard without session should redirect to /login
    for path in ["/dashboard", "/dashboard/logs", "/dashboard/workbench", "/dashboard/keys"]:
        res = client.get(path)
        assert res.status_code == 302
        assert "/login" in res.headers["Location"]
        assert "next=" in res.headers["Location"]

def test_demo_user_login_success(client):
    # Test logging in with seeded demo developer account
    res = client.post("/login", data={
        "email": "developer@civicpulse.dev",
        "password": "Password123!"
    }, follow_redirects=True)
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Demo Developer" in html
    assert "Sign Out" in html

def test_invalid_credentials_rejected(client):
    res = client.post("/login", data={
        "email": "developer@civicpulse.dev",
        "password": "WrongPassword999!"
    })
    assert res.status_code == 401
    html = res.get_data(as_text=True)
    assert "Invalid email or password" in html

def test_user_signup_and_auto_key_provisioning(client):
    test_email = f"test.dev.{secrets.token_hex(4)}@argus-test.org"
    res = client.post("/signup", data={
        "name": "Jordan Lee",
        "email": test_email,
        "password": "MySecurePassword123"
    }, follow_redirects=True)
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Jordan" in html

    # Verify key was automatically issued
    user_keys = db.get_user_keys(test_email)
    assert len(user_keys) >= 1
    assert user_keys[0]["tier"] == "free"
    assert user_keys[0]["key_hash"].startswith("argus_free_") or user_keys[0]["key_hash"].startswith("civic_free_")

def test_duplicate_signup_rejected(client):
    # Signing up with existing demo user email should fail
    res = client.post("/signup", data={
        "name": "Impostor",
        "email": "developer@civicpulse.dev",
        "password": "Password123!"
    })
    assert res.status_code == 400
    html = res.get_data(as_text=True)
    assert "already exists" in html

def test_user_logout(client):
    # Log in first
    client.post("/login", data={
        "email": "developer@civicpulse.dev",
        "password": "Password123!"
    })

    # Access dashboard - should succeed
    dash_res = client.get("/dashboard")
    assert dash_res.status_code == 200

    # Log out
    logout_res = client.get("/logout", follow_redirects=True)
    assert logout_res.status_code == 200
    html = logout_res.get_data(as_text=True)
    assert "You have been signed out" in html
    assert "Sign In" in html

    # Subsequent access to dashboard should redirect again
    retry_dash = client.get("/dashboard")
    assert retry_dash.status_code == 302
    assert "/login" in retry_dash.headers["Location"]
