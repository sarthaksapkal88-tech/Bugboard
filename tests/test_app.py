"""Unit tests for BugBoard application."""
import os
import sys
import tempfile
import pytest

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app, init_db


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app.config["TESTING"] = True
    os.environ["DATABASE_PATH"] = db_path

    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

    os.close(db_fd)
    os.unlink(db_path)


def _create_issue(client, title="Test Issue", description="Desc",
                  priority="Medium", created_by="Tester"):
    """Helper to create an issue and return the response."""
    return client.post("/create", data={
        "title": title,
        "description": description,
        "priority": priority,
        "created_by": created_by,
    }, follow_redirects=True)


# ── Dashboard ──────────────────────────────────────────────

def test_dashboard_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"BugBoard" in resp.data


def test_dashboard_empty_state(client):
    resp = client.get("/")
    assert b"No issues found" in resp.data


def test_dashboard_shows_stats(client):
    _create_issue(client, title="Bug A")
    _create_issue(client, title="Bug B")
    resp = client.get("/")
    assert b"Total Issues" in resp.data


# ── Health endpoint ────────────────────────────────────────

def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"
    assert data["app"] == "BugBoard"


# ── Create Issue ───────────────────────────────────────────

def test_create_page_loads(client):
    resp = client.get("/create")
    assert resp.status_code == 200
    assert b"Create New Issue" in resp.data


def test_create_issue(client):
    resp = _create_issue(client, title="Login button broken",
                         description="Button does not respond",
                         priority="High", created_by="Sarthak")
    assert resp.status_code == 200
    assert b"Login button broken" in resp.data
    assert b"Issue created successfully" in resp.data


def test_create_issue_missing_title(client):
    resp = client.post("/create", data={
        "title": "",
        "description": "No title provided",
        "priority": "Low",
        "created_by": "Test",
    }, follow_redirects=True)
    assert b"Title is required" in resp.data


def test_create_issue_default_created_by(client):
    resp = _create_issue(client, title="Minimal issue", created_by="")
    assert resp.status_code == 200
    assert b"Anonymous" in resp.data


# ── Edit Issue ─────────────────────────────────────────────

def test_edit_page_loads(client):
    _create_issue(client, title="Edit me")
    resp = client.get("/edit/1")
    assert resp.status_code == 200
    assert b"Edit me" in resp.data
    assert b"Edit Issue" in resp.data


def test_edit_issue(client):
    _create_issue(client, title="Old title", priority="Low")
    resp = client.post("/edit/1", data={
        "title": "Updated title",
        "description": "Updated desc",
        "priority": "Critical",
        "status": "In Progress",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Updated title" in resp.data
    assert b"Issue updated successfully" in resp.data


def test_edit_nonexistent_issue_redirects(client):
    """App redirects to dashboard with error flash when issue not found."""
    resp = client.get("/edit/999", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Issue not found" in resp.data


# ── Delete Issue ───────────────────────────────────────────

def test_delete_issue(client):
    _create_issue(client, title="Delete me")
    # Verify it exists
    resp = client.get("/")
    assert b"Delete me" in resp.data
    # Delete it
    resp = client.post("/delete/1", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Issue deleted" in resp.data
    assert b"Delete me" not in resp.data


def test_delete_nonexistent_issue(client):
    resp = client.post("/delete/999", follow_redirects=True)
    assert resp.status_code == 200


# ── Filters ────────────────────────────────────────────────

def test_filter_by_status(client):
    _create_issue(client, title="Open bug", priority="High")
    resp = client.get("/?status=Open")
    assert resp.status_code == 200
    assert b"Open bug" in resp.data


def test_filter_by_priority(client):
    _create_issue(client, title="Critical bug", priority="Critical")
    _create_issue(client, title="Low bug", priority="Low")
    resp = client.get("/?priority=Critical")
    assert b"Critical bug" in resp.data
    assert b"Low bug" not in resp.data


def test_search(client):
    _create_issue(client, title="Payment gateway error", priority="High")
    _create_issue(client, title="UI alignment", priority="Low")
    resp = client.get("/?q=payment")
    assert b"Payment gateway error" in resp.data
    assert b"UI alignment" not in resp.data
