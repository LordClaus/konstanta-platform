"""Object storage for job photos (Cloudflare R2 / any S3-compatible bucket).

The host filesystem is ephemeral, so uploads are re-encoded to WEBP (which also
strips EXIF/polyglot payloads) and pushed to R2; only the resulting public URL is
persisted. Returns ``None`` when storage is not configured so callers can 503.
"""

from __future__ import annotations

import io
import logging
import uuid

from fastapi import HTTPException, status

from app.config import get_settings

log = logging.getLogger("api.storage")

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _reencode_webp(raw: bytes) -> bytes:
    from PIL import Image, UnidentifiedImageError

    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
        out = io.BytesIO()
        img.convert("RGB").save(out, format="WEBP", quality=82)
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or corrupt image") from exc
    return out.getvalue()


def upload_job_image(job_id: str, content_type: str | None, raw: bytes) -> str:
    """Validate, re-encode and upload an image; return its public URL."""
    s = get_settings()
    if not s.storage_configured:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Image storage is not configured")
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only JPEG/PNG/WebP allowed")
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large (max 5 MB)")

    body = _reencode_webp(raw)
    key = f"jobs/{job_id}/{uuid.uuid4().hex}.webp"
    try:
        import boto3

        client = boto3.client(
            "s3",
            endpoint_url=s.r2_endpoint,
            aws_access_key_id=s.r2_key,
            aws_secret_access_key=s.r2_secret,
            region_name="auto",
        )
        client.put_object(Bucket=s.r2_bucket, Key=key, Body=body, ContentType="image/webp")
    except Exception as exc:  # noqa: BLE001
        log.error("R2 upload failed for job %s: %s", job_id, exc)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Image upload failed") from exc

    return f"{s.r2_public_url.rstrip('/')}/{key}"
