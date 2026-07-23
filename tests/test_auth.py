"""
Tests for signup, login, and the auth dependency, exercised through the real
HTTP layer (TestClient). This is "integration" style testing: instead of
calling Python functions directly, we send requests exactly like a real
client would, so we're also verifying routing, request validation, and
response shape — not just business logic.
"""

import pytest

SIGNUP_PAYLOAD = {
    "name": "Doe",
    "firstname": "Jane",
    "username": "janedoe",
    "email": "jane@example.com",
    "password": "S3cure-Pass!",
}


def signup(client, **overrides):
    payload = {**SIGNUP_PAYLOAD, **overrides}
    return client.post("/signup", json=payload)


def login(client, email=SIGNUP_PAYLOAD["email"], password=SIGNUP_PAYLOAD["password"]):
    # OAuth2PasswordRequestForm expects form-encoded data, not JSON — that's
    # why this is `data=` and the signup call above is `json=`.
    return client.post("/login", data={"username": email, "password": password})


def test_signup_creates_account(client):
    response = signup(client)
    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "Account successfully created"
    assert "id" in body


@pytest.mark.parametrize(
    "override, conflicting_field, expected_detail",
    [
        ({"username": "someone_else"}, "email", "Email already used"),
        ({"email": "someone_else@example.com"}, "username", "Username already used"),
    ],
)
def test_signup_rejects_duplicate_unique_fields(client, override, conflicting_field, expected_detail):
    """
    email and username are both unique columns (see db.py). Parametrizing
    this test lets us check both constraints with one test body instead of
    copy-pasting the same test twice with minor differences.
    """
    signup(client)
    response = signup(client, **override)
    assert response.status_code == 400
    assert response.json()["detail"] == expected_detail


def test_login_succeeds_with_correct_credentials(client):
    signup(client)
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_fails_with_wrong_password(client):
    signup(client)
    response = login(client, password="wrong-password")
    assert response.status_code == 401


def test_login_does_not_reveal_whether_the_account_exists(client):
    """
    A wrong password for a real account and a login attempt for an account
    that was never created should return the exact same error. If they
    differed, an attacker could use the response to figure out which emails
    are registered — see the dummy-hash comparison in authenticate_user().
    """
    signup(client)
    wrong_password_response = login(client, password="wrong-password")
    unknown_user_response = login(client, email="nobody@example.com")

    assert wrong_password_response.status_code == unknown_user_response.status_code == 401
    assert wrong_password_response.json()["detail"] == unknown_user_response.json()["detail"]


def test_login_rejects_username_in_place_of_email(client):
    """
    The OAuth2 form field is literally called "username", but this API's
    authenticate_user() only ever looks users up by email — so logging in
    with the actual username should fail. Worth asserting explicitly, since
    the field name is misleading otherwise.
    """
    signup(client)
    response = login(client, email=SIGNUP_PAYLOAD["username"])
    assert response.status_code == 401


def test_home_requires_authentication(client):
    response = client.get("/home")
    assert response.status_code == 401


def test_home_returns_welcome_message_for_authenticated_user(client):
    signup(client)
    token = login(client).json()["access_token"]
    response = client.get("/home", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"message": f"Welcome {SIGNUP_PAYLOAD['firstname']}"}


def test_protected_route_rejects_malformed_token(client):
    response = client.get("/home", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
