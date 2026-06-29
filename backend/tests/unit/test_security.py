"""Unit tests for password hashing, JWT round-trips and the age gate."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi import HTTPException

from app.core import security


def test_password_hash_roundtrip():
    h = security.hash_password("s3cret!")
    assert h != "s3cret!"
    assert security.verify_password("s3cret!", h)
    assert not security.verify_password("wrong", h)
    assert not security.verify_password("x", None)


def test_staff_token_roundtrip():
    token = security.create_staff_token(7, "alice", "admin")
    payload = security.decode_token(token)
    assert payload["sub"] == "7"
    assert payload["scope"] == "staff"
    assert payload["role"] == "admin"
    assert payload["username"] == "alice"


def test_candidate_token_roundtrip():
    token = security.create_candidate_token(42, "a@b.com")
    payload = security.decode_token(token)
    assert payload["scope"] == "candidate"
    assert payload["email"] == "a@b.com"


def test_decode_invalid_token_raises_401():
    with pytest.raises(HTTPException) as exc:
        security.decode_token("garbage.token.value")
    assert exc.value.status_code == 401


def test_assert_adult_blocks_minors():
    today = date.today()
    minor = date(today.year - 10, today.month, today.day)
    with pytest.raises(HTTPException) as exc:
        security.assert_adult(minor)
    assert exc.value.status_code == 400
    # An adult passes silently.
    security.assert_adult(date(today.year - 30, 1, 1))
