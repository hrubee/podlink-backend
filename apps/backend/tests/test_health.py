"""
Smoke tests — verify the app starts cleanly and core endpoints respond.
These run in GitHub Actions CI using SQLite with a test SECRET_KEY.
"""
import os
import pytest
from fastapi.testclient import TestClient

# Ensure test env vars are set before importing app
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-not-real-32chars!")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_ci.db")


@pytest.fixture(scope="module")
def client():
    from main import app
    with TestClient(app) as c:
        yield c


def test_root(client):
    """App responds on /"""
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "online"


def test_health(client):
    """Railway health check endpoint is always 200."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_db(client):
    """DB health check works (SQLite in CI)."""
    resp = client.get("/health/db")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


def test_login_unauthenticated(client):
    """Protected endpoint returns 401 without a token."""
    resp = client.get("/v1/users/me")
    assert resp.status_code in (401, 403)


def test_signup_missing_fields(client):
    """Signup with missing fields returns a validation error."""
    resp = client.post("/v1/signup", json={"email": "bad"})
    assert resp.status_code == 422


def test_rate_limit_not_triggered_single_request(client):
    """A single login attempt does NOT hit the rate limit."""
    resp = client.post(
        "/v1/login/access-token",
        data={"username": "notexist@test.com", "password": "wrongpassword"},
    )
    # Should be 400 (bad credentials), not 429 (rate limit)
    assert resp.status_code == 400
