"""
Tests for the /account endpoints (view, update, delete).

Every test here first has to sign up and log in to get a token — that's the
cost of testing a protected route through the real HTTP layer instead of
mocking authentication away. _authenticated_client() exists purely to avoid
repeating that setup in every single test.
"""

from datetime import date

from db import Event, SessionLocal

SIGNUP_PAYLOAD = {
    "name": "Doe",
    "firstname": "Jane",
    "username": "janedoe",
    "email": "jane@example.com",
    "password": "S3cure-Pass!",
}


def _authenticated_client(client, payload=None):
    payload = payload or SIGNUP_PAYLOAD
    signup_response = client.post("/signup", json=payload)
    token = client.post(
        "/login",
        data={"username": payload["email"], "password": payload["password"]},
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, signup_response.json()["id"]


def test_get_account_returns_profile(client):
    client, _ = _authenticated_client(client)
    response = client.get("/account")
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == SIGNUP_PAYLOAD["email"]
    assert body["username"] == SIGNUP_PAYLOAD["username"]


def test_get_account_requires_authentication(client):
    response = client.get("/account")
    assert response.status_code == 401


def test_update_account_changes_profile_fields(client):
    client, _ = _authenticated_client(client)
    response = client.patch(
        "/account",
        json={
            "name": "Doe",
            "firstname": "Janet",
            "email": SIGNUP_PAYLOAD["email"],
            "phone": "0712345678",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["firstname"] == "Janet"
    assert body["phone"] == "0712345678"


def test_update_account_rejects_email_already_used_by_another_user(client):
    client.post("/signup", json=SIGNUP_PAYLOAD)
    other_user = {**SIGNUP_PAYLOAD, "username": "otheruser", "email": "other@example.com"}
    client.post("/signup", json=other_user)

    token = client.post(
        "/login",
        data={"username": other_user["email"], "password": other_user["password"]},
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    response = client.patch(
        "/account",
        json={
            "name": other_user["name"],
            "firstname": other_user["firstname"],
            "email": SIGNUP_PAYLOAD["email"],
            "phone": None,
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already used"


def test_delete_account_removes_user_and_invalidates_access(client):
    client, _ = _authenticated_client(client)
    response = client.delete("/account")
    assert response.status_code == 200

    # The token itself is still cryptographically valid — JWTs can't be
    # revoked early. What actually blocks reuse is get_current_user() looking
    # the user up in the database and finding nothing.
    follow_up = client.get("/account")
    assert follow_up.status_code == 401


def test_delete_account_fails_when_user_has_related_events(client):
    """
    users.id_user is referenced by events.id_user (see db.py). Deleting a
    user who still owns events should be blocked by the database's foreign
    key constraint, which the route catches as a SQLAlchemyError and turns
    into a 400 instead of a raw 500.
    """
    client, user_id = _authenticated_client(client)

    with SessionLocal() as db:
        db.add(
            Event(
                id_user=user_id,
                event_type="wedding",
                event_date=date.today(),
                token="evt-token-1",
            )
        )
        db.commit()

    response = client.delete("/account")
    assert response.status_code == 400
    assert "related data" in response.json()["detail"]
