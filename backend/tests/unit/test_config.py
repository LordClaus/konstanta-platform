"""The production guard on Settings: a weak/default JWT secret must fail fast."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_rejects_default_jwt_secret():
    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret="change-me-in-production")


def test_production_rejects_short_jwt_secret():
    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret="too-short")


def test_production_accepts_strong_jwt_secret():
    s = Settings(environment="production", jwt_secret="x" * 40)
    assert s.environment == "production"


def test_development_allows_default_secret():
    # The default is fine outside production (local dev / tests).
    s = Settings(environment="development", jwt_secret="change-me-in-production")
    assert s.jwt_secret == "change-me-in-production"
