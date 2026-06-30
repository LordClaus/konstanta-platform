"""Unit tests for the image storage service: WEBP re-encode + guard rails.

No network here — the test environment has no R2 configured, so uploads short-
circuit to 503 before any S3 call, and the re-encode path runs purely in-process.
"""

from __future__ import annotations

import io

import pytest
from fastapi import HTTPException

from app.services import storage


def _png_bytes() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (2, 2), (255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


def test_reencode_webp_roundtrips_a_real_image():
    out = storage._reencode_webp(_png_bytes())
    assert out[:4] == b"RIFF" and out[8:12] == b"WEBP"  # WEBP container header


def test_reencode_webp_rejects_garbage():
    with pytest.raises(HTTPException) as exc:
        storage._reencode_webp(b"definitely not an image")
    assert exc.value.status_code == 400


def test_upload_requires_configured_storage(monkeypatch):
    # Force "storage unconfigured" regardless of any local .env → 503 before any
    # validation or network call.
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "r2_endpoint", None, raising=False)
    with pytest.raises(HTTPException) as exc:
        storage.upload_job_image("job1", "image/png", _png_bytes())
    assert exc.value.status_code == 503
