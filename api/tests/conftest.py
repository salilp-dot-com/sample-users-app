"""Shared test setup.

The tests run against a real PostgreSQL database named `users_test`, which is dropped and
recreated on every run (your `users_db` is never touched). Point TEST_ADMIN_DATABASE_URL at
any database on the server the test user can connect to; CI uses a Postgres service container.
"""

import os
import uuid

import psycopg
import pytest

# --- Configure the app BEFORE importing it: app.config reads env vars at import time. ---
ADMIN_URL = os.environ.get(
    "TEST_ADMIN_DATABASE_URL",
    "postgresql://postgres:Password123!@localhost:5433/postgres",  # docker-compose.yml
)
TEST_DB = "users_test"
TEST_URL = ADMIN_URL.rsplit("/", 1)[0] + f"/{TEST_DB}"

os.environ.update(
    DATABASE_URL=TEST_URL,
    JWT_SECRET="test-only-jwt-secret-0123456789abcdef",  # >= 32 bytes for HS256
    CARD_KEY_PROVIDER="env",
    # Fixed test-only AES-256 key (32 zero-to-31 bytes), never used outside tests.
    CARD_ENCRYPTION_KEYS="1:AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8=",
    DEFAULT_USER_EMAIL="admin@example.com",
    DEFAULT_USER_PASSWORD="admin-test-password",
    AUTH_COOKIE_SECURE="false",
)

import app.security  # noqa: E402

# Real PBKDF2 cost (600k iterations) makes every signup/login ~0.5s; tests don't need it.
app.security.PBKDF2_ITERATIONS = 1_000

from fastapi.testclient import TestClient  # noqa: E402

DEFAULT_PASSWORD = "correct-horse-1"


def _recreate_test_database() -> None:
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
        conn.execute(f"CREATE DATABASE {TEST_DB}")


@pytest.fixture(scope="session")
def client():
    """One app instance for the whole run. Startup runs the yoyo migrations."""
    _recreate_test_database()
    from app.main import app as fastapi_app

    with TestClient(fastapi_app) as c:
        yield c


@pytest.fixture(autouse=True)
def _no_leftover_cookies(client):
    """Cookie-auth tests leave an auth cookie in the shared client; start each test clean."""
    client.cookies.clear()
    yield
    client.cookies.clear()


@pytest.fixture
def db():
    with psycopg.connect(TEST_URL) as conn:
        yield conn


def unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:10]}@example.com"


def user_payload(**overrides) -> dict:
    payload = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "credit_card_number": "4111 1111 1111 1111",
        "email": unique_email(),
        "password": DEFAULT_PASSWORD,
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def new_user(client):
    """Create a user through the API; returns (user_json, password)."""

    def _create(**overrides):
        payload = user_payload(**overrides)
        res = client.post("/users", json=payload)
        assert res.status_code == 201, res.text
        return res.json(), payload["password"]

    return _create


@pytest.fixture
def auth_headers(client, new_user):
    """Bearer headers for a freshly created user."""
    user, password = new_user()
    res = client.post("/login", json={"email": user["email"], "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
