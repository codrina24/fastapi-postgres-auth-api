"""
Unit tests for jwt_auth.py, calling the functions directly instead of going
through HTTP. This is a different strategy from test_auth.py: faster, more
focused on one function at a time, and it lets us test things — like an
already-expired token — that would be awkward to trigger through the API
itself (we'd have to actually wait 15 minutes).
"""

from datetime import timedelta

import pytest
from fastapi import HTTPException

from db import SessionLocal, User
from jwt_auth import create_access_token, get_current_user


def _create_user(email="unit@example.com"):
    with SessionLocal() as db:
        user = User(
            name="Unit",
            firstname="Test",
            username="unittest",
            email=email,
            password="irrelevant-for-this-test",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id_user


def test_create_access_token_produces_a_valid_jwt_shape():
    token = create_access_token(data={"sub": "42"})
    assert isinstance(token, str)
    # a JWT is three base64 segments separated by dots: header.payload.signature
    assert token.count(".") == 2


def test_get_current_user_returns_the_matching_user():
    user_id = _create_user()
    token = create_access_token(data={"sub": str(user_id)})

    # get_current_user is normally called by FastAPI's dependency injection,
    # which supplies `token` for us on every request. Called directly like
    # this, it behaves like any other Python function.
    user = get_current_user(token=token)

    assert user.id_user == user_id


def test_get_current_user_rejects_an_expired_token():
    user_id = _create_user()
    expired_token = create_access_token(
        data={"sub": str(user_id)}, expires_delta=timedelta(seconds=-1)
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=expired_token)

    assert exc_info.value.status_code == 401


def test_get_current_user_rejects_a_token_for_a_deleted_user():
    # A syntactically valid, correctly signed token whose subject simply
    # doesn't exist in the database anymore — e.g. the account was deleted
    # after the token was issued.
    token = create_access_token(data={"sub": "999999"})

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token)

    assert exc_info.value.status_code == 401
