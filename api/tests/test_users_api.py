"""End-to-end tests of the users REST API (bearer-token auth)."""

import pytest
from conftest import DEFAULT_PASSWORD, unique_email, user_payload

from app.crypto import decrypt_card


def test_health_reports_status_and_version(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert "version" in res.json()


# --- Sign-up -----------------------------------------------------------------


def test_signup_masks_card_and_hides_secrets(client):
    res = client.post("/users", json=user_payload(email="Mixed.Case@Example.com"))
    assert res.status_code == 201
    body = res.json()
    assert body["credit_card_number"] == "**** **** **** 1111"
    assert body["email"] == "mixed.case@example.com"  # stored lower-case
    assert "password" not in body
    assert "salt" not in body


def test_signup_duplicate_email_is_conflict(client):
    email = unique_email()
    assert client.post("/users", json=user_payload(email=email)).status_code == 201
    res = client.post("/users", json=user_payload(email=email.upper()))
    assert res.status_code == 409


@pytest.mark.parametrize(
    "overrides",
    [
        {"credit_card_number": "12ab"},
        {"credit_card_number": "123"},
        {"password": "short"},
        {"email": "not-an-email"},
        {"first_name": ""},
    ],
)
def test_signup_validation_errors(client, overrides):
    assert client.post("/users", json=user_payload(**overrides)).status_code == 422


def test_secrets_are_not_stored_in_plaintext(client, db, new_user):
    user, password = new_user(credit_card_number="5500-0000-0000-0004")
    row = db.execute(
        "SELECT password, salt, credit_card_encrypted, card_key_version, card_last4 "
        "FROM users WHERE id = %s",
        (user["id"],),
    ).fetchone()
    stored_hash, salt, card_blob, key_version, last4 = row
    assert stored_hash != password and len(salt) == 32
    assert b"5500000000000004" not in bytes(card_blob)
    assert decrypt_card(card_blob, key_version) == "5500000000000004"
    assert last4 == "0004"


# --- Login -------------------------------------------------------------------


def test_login_returns_bearer_token(client, new_user):
    user, password = new_user()
    res = client.post("/login", json={"email": user["email"], "password": password})
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"].count(".") == 2  # header.payload.signature
    assert body["user_id"] == user["id"]


@pytest.mark.parametrize("which", ["wrong password", "unknown email"])
def test_login_failures_give_the_same_error(client, new_user, which):
    user, _ = new_user()
    email = user["email"] if which == "wrong password" else unique_email()
    res = client.post("/login", json={"email": email, "password": "not-the-password"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password"


def test_default_user_from_migration_can_log_in(client):
    res = client.post(
        "/login", json={"email": "admin@example.com", "password": "admin-test-password"}
    )
    assert res.status_code == 200


# --- Protected endpoints -----------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/users"),
        ("GET", "/users/1"),
        ("PUT", "/users/1"),
        ("PATCH", "/users/1"),
        ("DELETE", "/users/1"),
        ("GET", "/me"),
    ],
)
def test_protected_endpoints_require_auth(client, method, path):
    assert client.request(method, path, json={}).status_code == 401


def test_invalid_token_is_rejected(client):
    res = client.get("/users", headers={"Authorization": "Bearer not.a.jwt"})
    assert res.status_code == 401


def test_list_and_get_users(client, auth_headers, new_user):
    user, _ = new_user()
    listed = client.get("/users", headers=auth_headers).json()
    assert user["id"] in [u["id"] for u in listed]
    res = client.get(f"/users/{user['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == user


def test_get_missing_user_is_404(client, auth_headers):
    assert client.get("/users/999999", headers=auth_headers).status_code == 404


def test_patch_changes_only_sent_fields(client, auth_headers, new_user):
    user, _ = new_user()
    res = client.patch(f"/users/{user['id']}", json={"last_name": "King"}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == {**user, "last_name": "King"}


def test_put_replaces_user_and_password(client, auth_headers, new_user):
    user, old_password = new_user()
    replacement = user_payload(
        first_name="Grace",
        last_name="Hopper",
        email=user["email"],
        credit_card_number="5500000000000004",
        password="brand-new-pass",
    )
    res = client.put(f"/users/{user['id']}", json=replacement, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["first_name"] == "Grace"
    assert res.json()["credit_card_number"] == "**** **** **** 0004"

    login = {"email": user["email"]}
    assert client.post("/login", json={**login, "password": old_password}).status_code == 401
    assert client.post("/login", json={**login, "password": "brand-new-pass"}).status_code == 200


def test_put_requires_every_field(client, auth_headers, new_user):
    user, _ = new_user()
    res = client.put(f"/users/{user['id']}", json={"first_name": "X"}, headers=auth_headers)
    assert res.status_code == 422


def test_update_to_taken_email_is_conflict(client, auth_headers, new_user):
    first, _ = new_user()
    second, _ = new_user()
    res = client.patch(
        f"/users/{second['id']}", json={"email": first["email"]}, headers=auth_headers
    )
    assert res.status_code == 409


def test_delete_user(client, auth_headers, new_user):
    user, _ = new_user()
    assert client.delete(f"/users/{user['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/users/{user['id']}", headers=auth_headers).status_code == 404
    assert client.delete(f"/users/{user['id']}", headers=auth_headers).status_code == 404


def test_me_with_bearer_token(client, new_user):
    user, _ = new_user()
    token = client.post(
        "/login", json={"email": user["email"], "password": DEFAULT_PASSWORD}
    ).json()["access_token"]
    res = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["id"] == user["id"]
