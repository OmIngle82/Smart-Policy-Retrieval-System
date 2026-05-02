"""

File: backend/tests/test_api.py

Responsibility: PyTest unit test suite for the FastAPI backend.
Tests cover:
  - Health check endpoint
  - User registration and login (auth flow)
  - JWT token validation (protected route access)
  - Query endpoint — success, missing token, RBAC enforcement
  - Admin document registration

Usage (from project root):
    pytest backend/tests/ -v

VIVA NOTE: These tests ensure that every layer of the backend works correctly
even after team members make changes — protecting the main branch from bugs.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from backend.main import app

# ── Test Client ────────────────────────────────────────────────────────────────
# TestClient lets us simulate HTTP requests to the FastAPI app without
# actually starting a real server — fully in-memory and very fast.
client = TestClient(app)

# ── Mock Data ──────────────────────────────────────────────────────────────────
TEST_USER    = {"username": "test_analyst", "email": "analyst@test.com", "password": "SecurePass123!"}
ADMIN_USER   = {"username": "test_admin",   "email": "admin@test.com",   "password": "AdminPass456!"}
QUERY_BODY   = {"question": "What is the scholarship eligibility?", "inference_mode": "local"}


# ── Helper: Get a valid JWT token for tests ────────────────────────────────────
def _get_token(username: str, password: str) -> str:
    """Logs in and returns the JWT access token."""
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    return resp.json()["access_token"]


# ── Test: Health Check ─────────────────────────────────────────────────────────
def test_health_check():
    """The root endpoint should return 200 and a status ok message."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── Test: Auth — Registration ──────────────────────────────────────────────────
@patch("backend.main.get_db_connection")
def test_register_new_user(mock_db):
    """
    A new user should register successfully.
    We mock the DB connection to avoid needing a real MySQL instance.
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.lastrowid = 42
    mock_conn.cursor.return_value = mock_cursor
    mock_db.return_value = mock_conn

    resp = client.post("/api/v1/auth/register", json=TEST_USER)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    mock_cursor.execute.assert_called()  # Verify an INSERT was executed


@patch("backend.main.get_db_connection")
def test_register_duplicate_user(mock_db):
    """Registering the same email twice should return a 409 Conflict."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception("Duplicate entry 'analyst@test.com'")
    mock_conn.cursor.return_value = mock_cursor
    mock_db.return_value = mock_conn

    resp = client.post("/api/v1/auth/register", json=TEST_USER)
    assert resp.status_code == 409


# ── Test: Auth — Login ─────────────────────────────────────────────────────────
@patch("backend.main.get_db_connection")
@patch("backend.main.bcrypt.checkpw", return_value=True)
def test_login_success(mock_bcrypt, mock_db):
    """A valid login should return a JWT access_token."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    # Simulate user found in DB
    mock_cursor.fetchone.return_value = {
        "id": 1, "username": "test_analyst", "password_hash": "hashed"
    }
    # Simulate roles
    mock_cursor.fetchall.return_value = [{"role_name": "analyst"}]
    mock_conn.cursor.return_value = mock_cursor
    mock_db.return_value = mock_conn

    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "test_analyst", "password": "SecurePass123!"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@patch("backend.main.get_db_connection")
@patch("backend.main.bcrypt.checkpw", return_value=False)
def test_login_wrong_password(mock_bcrypt, mock_db):
    """A login with wrong password should return 401 Unauthorized."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {
        "id": 1, "username": "test_analyst", "password_hash": "hashed"
    }
    mock_conn.cursor.return_value = mock_cursor
    mock_db.return_value = mock_conn

    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "test_analyst", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


# ── Test: Query Endpoint ───────────────────────────────────────────────────────
def test_query_without_token():
    """Calling /query without a JWT should return 401."""
    # Ensure no overrides are active for this test
    app.dependency_overrides = {}
    resp = client.post("/api/v1/query", json=QUERY_BODY)
    assert resp.status_code == 401


@patch("backend.main.cache_service")
@patch("backend.main._get_allowed_sources", return_value=None)
@patch("backend.main.run_rag_query", return_value={
    "answer": "The scholarship amount is Rs. 50,000.",
    "citations": [{"document_name": "policy.pdf", "page_number": 5, "clause": "Section 3"}],
})
def test_query_success(mock_rag, mock_sources, mock_cache):
    """
    A valid authenticated query should return status=success and the correct schema.
    We use dependency_overrides to simulate a logged-in user.
    """
    from backend.main import _get_current_user
    app.dependency_overrides[_get_current_user] = lambda: {"user_id": 1, "roles": ["analyst"]}
    mock_cache.get.return_value = None
    
    try:
        resp = client.post(
            "/api/v1/query",
            json=QUERY_BODY,
            headers={"Authorization": "Bearer mock_token"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert "answer" in body["data"]
    finally:
        app.dependency_overrides = {}


@patch("backend.main._get_allowed_sources", return_value=[])  # No public docs available
def test_query_general_user_no_public_docs(mock_sources):
    """
    A General User with no accessible documents should receive 403 Forbidden.
    """
    from backend.main import _get_current_user
    app.dependency_overrides[_get_current_user] = lambda: {"user_id": 5, "roles": ["general_user"]}
    
    try:
        resp = client.post(
            "/api/v1/query",
            json=QUERY_BODY,
            headers={"Authorization": "Bearer mock_token"},
        )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides = {}


# ── Test: Admin Endpoint ───────────────────────────────────────────────────────
def test_admin_route_non_admin_user():
    """A non-admin user should receive 403 when accessing admin endpoints."""
    from backend.main import _get_current_user
    app.dependency_overrides[_get_current_user] = lambda: {"user_id": 1, "roles": ["analyst"]}
    
    try:
        # Provide a dummy file to avoid 422 error
        files = {"file": ("test.pdf", b"dummy content", "application/pdf")}
        resp = client.post(
            "/api/v1/admin/documents",
            data={"display_name": "Test Doc"},
            files=files,
            headers={"Authorization": "Bearer mock_token"},
        )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides = {}
