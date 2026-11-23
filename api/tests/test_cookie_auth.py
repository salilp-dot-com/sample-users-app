"""Cookie-based auth: HttpOnly cookie, CSRF header check, /me and /logout."""

import pytest


@pytest.fixture
def cookie_login(client, new_user):
    """Log a fresh user in with ?cookie=true; the TestClient keeps the cookie."""
    user, password = new_user()
    res = client.post("/login?cookie=true", json={"email": user["email"], "password": password})
    assert res.status_code == 200, res.text
    return user, res


def test_cookie_login_sets_httponly_cookie_and_hides_token(cookie_login):
    _, res = cookie_login
    assert res.json()["access_token"] is None
    assert res.json()["token_type"] == "cookie"
    set_cookie = res.headers["set-cookie"].lower()
    assert set_cookie.startswith("access_token=")
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie


def test_cookie_authenticates_reads(client, cookie_login):
    user, _ = cookie_login
    assert client.get("/users").status_code == 200
    me = client.get("/me")
    assert me.status_code == 200
    assert me.json()["id"] == user["id"]


def test_cookie_write_without_csrf_header_is_forbidden(client, cookie_login):
    user, _ = cookie_login
    res = client.patch(f"/users/{user['id']}", json={"first_name": "Mallory"})
    assert res.status_code == 403
    assert "CSRF" in res.json()["detail"]


def test_cookie_write_with_csrf_header_is_allowed(client, cookie_login):
    user, _ = cookie_login
    res = client.patch(
        f"/users/{user['id']}",
        json={"first_name": "Alice"},
        headers={"X-Requested-With": "fetch"},
    )
    assert res.status_code == 200
    assert res.json()["first_name"] == "Alice"


def test_bearer_write_needs_no_csrf_header(client, auth_headers, new_user):
    user, _ = new_user()
    res = client.patch(f"/users/{user['id']}", json={"first_name": "Bob"}, headers=auth_headers)
    assert res.status_code == 200


def test_logout_clears_cookie(client, cookie_login):
    res = client.post("/logout")
    assert res.status_code == 204
    assert "max-age=0" in res.headers["set-cookie"].lower()
    assert client.get("/me").status_code == 401
