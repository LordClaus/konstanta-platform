"""Shared test fixtures.

The suite runs against a throwaway SQLite database (no PostgreSQL needed in CI),
so the environment is configured *before* the app is imported — that is what
makes ``get_settings()`` pick up the test DB URL and secret.
"""

from __future__ import annotations

import os
import pathlib

# ── Configure the environment BEFORE importing the app ────────────────────────
_TEST_DB = pathlib.Path(__file__).parent / "_test.db"
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "test-secret-key-at-least-32-bytes-long!!"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB.as_posix()}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()  # ensure the test env above wins

from app.core import security  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.main import app  # noqa: E402

# Rate limiting would make repeated auth calls flaky; disable it under test.
limiter.enabled = False


@pytest.fixture(scope="session", autouse=True)
def _fresh_db_file():
    """Start every test session from an empty database file."""
    if _TEST_DB.exists():
        _TEST_DB.unlink()
    yield
    if _TEST_DB.exists():
        try:
            _TEST_DB.unlink()
        except OSError:
            pass


@pytest.fixture(scope="session")
def client():
    """A TestClient whose context manager runs the app lifespan (schema create +
    category seed + cache warm)."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def admin_headers() -> dict:
    """Authorization header for an admin staff token (no DB row required —
    ``require_role`` only validates the JWT)."""
    token = security.create_staff_token(1, "admin", "admin")
    return {"Authorization": f"Bearer {token}"}
