"""Tests for the API endpoints using an isolated test database."""
import sys
import os
from app.main import app
# Disable rate limiting during tests
app.state.limiter.enabled = False   
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app import models
from app.main import app

# ---- Set up an in-memory SQLite test database ----
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_signup_creates_student():
    """A new signup creates a student account."""
    response = client.post("/auth/signup", json={
        "full_name": "Test User",
        "email": "newuser@test.com",
        "password": "password123",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert data["role"] == "student"   # public signups are always students


def test_duplicate_email_rejected():
    """Signing up with an already-used email is rejected."""
    client.post("/auth/signup", json={
        "full_name": "First",
        "email": "dupe@test.com",
        "password": "password123",
    })
    response = client.post("/auth/signup", json={
        "full_name": "Second",
        "email": "dupe@test.com",
        "password": "password123",
    })
    assert response.status_code == 400


def test_login_with_correct_credentials():
    """Login succeeds with correct credentials and returns a token."""
    client.post("/auth/signup", json={
        "full_name": "Login User",
        "email": "login@test.com",
        "password": "mypassword",
    })
    response = client.post("/auth/login", json={
        "email": "login@test.com",
        "password": "mypassword",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_with_wrong_password_fails():
    """Login fails with a wrong password."""
    client.post("/auth/signup", json={
        "full_name": "Wrong Pass",
        "email": "wrongpass@test.com",
        "password": "correctpassword",
    })
    response = client.post("/auth/login", json={
        "email": "wrongpass@test.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


def test_protected_route_requires_token():
    """Accessing a protected route without a token is rejected."""
    response = client.get("/exams/available")
    assert response.status_code in (401, 403)


def test_interview_creation_and_monitoring_flow():
    """Interview sessions can be created and monitoring events stored with risk scoring."""
    client.post("/auth/signup", json={
        "full_name": "Admin User",
        "email": "admin-interview@test.com",
        "password": "password123",
    })
    admin_login = client.post("/auth/login", json={
        "email": "admin-interview@test.com",
        "password": "password123",
    })
    admin_token = admin_login.json()["access_token"]

    client.post("/auth/signup", json={
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "password": "password123",
    })
    candidate_login = client.post("/auth/login", json={
        "email": "jane@example.com",
        "password": "password123",
    })
    candidate_token = candidate_login.json()["access_token"]

    create = client.post(
        "/interviews",
        json={
            "candidate_name": "Jane Doe",
            "candidate_email": "jane@example.com",
            "interview_type": "technical",
            "allowlist": ["https://docs.example.com"],
            "status": "scheduled",
            "started_at": "2026-01-01T10:00:00Z",
            "ends_at": "2030-01-01T11:00:00Z",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create.status_code == 200, create.text
    interview_id = create.json()["id"]

    recruiter_consent = client.post(
        f"/interviews/{interview_id}/consent",
        json={"candidate_consent": True, "required_components": ["browser_extension", "desktop_companion"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert recruiter_consent.status_code == 403

    consent = client.post(
        f"/interviews/{interview_id}/consent",
        json={"candidate_consent": True, "required_components": ["browser_extension", "desktop_companion"]},
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert consent.status_code == 200, consent.text

    browser_event = client.post(
        f"/interviews/{interview_id}/browser-events",
        json={
            "event_type": "LOCALHOST_ACCESS",
            "details": "Opened localhost testing page",
            "url": "http://127.0.0.1:3000",
            "tab_id": 11,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert browser_event.status_code == 200, browser_event.text

    desktop_event = client.post(
        f"/interviews/{interview_id}/desktop-events",
        json={
            "event_type": "APP_SWITCH",
            "app_name": "VS Code",
            "process_name": "Code.exe",
            "window_title": "App.tsx",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert desktop_event.status_code == 200, desktop_event.text

    risk_response = client.get(
        f"/interviews/{interview_id}/risk",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert risk_response.status_code == 200, risk_response.text
    risk_data = risk_response.json()
    assert risk_data["level"] in {"low", "medium", "high"}
    assert risk_data["score"] >= 0


def test_interview_rejects_invalid_token_and_expired_session():
    """Interview APIs reject invalid auth and expired sessions while preserving exam functionality."""
    bad = client.get("/interviews")
    assert bad.status_code in (401, 403)

    client.post("/auth/signup", json={
        "full_name": "Session User",
        "email": "session-user@test.com",
        "password": "password123",
    })
    login = client.post("/auth/login", json={
        "email": "session-user@test.com",
        "password": "password123",
    })
    token = login.json()["access_token"]

    create = client.post(
        "/interviews",
        json={
            "candidate_name": "Candidate A",
            "candidate_email": "candidate-a@example.com",
            "interview_type": "hr",
            "allowlist": [],
            "status": "active",
            "started_at": "2026-01-01T10:00:00Z",
            "ends_at": "2026-01-01T10:05:00Z",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create.status_code == 200, create.text
    interview_id = create.json()["id"]

    expiry = client.post(
        f"/interviews/{interview_id}/status",
        json={"status": "completed"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert expiry.status_code == 200, expiry.text

    reject = client.post(
        f"/interviews/{interview_id}/browser-events",
        json={"event_type": "TAB_SWITCH", "details": "bad"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert reject.status_code in (400, 409, 403), reject.text