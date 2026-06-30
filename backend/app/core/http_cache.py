"""Conditional HTTP caching for the hot public read endpoints.

The job / category / review lists are read-mostly and already served from the
in-process :class:`AppCache` (no DB hit). This adds the HTTP layer on top: a short
``Cache-Control`` max-age plus a content ``ETag``, so browsers and any CDN/proxy
can revalidate cheaply — a request whose ``If-None-Match`` matches the current
ETag gets ``304 Not Modified`` with no body.

Writes mutate ``AppCache`` in place, so a changed payload yields a new ETag on the
very next read; downstream caches converge within ``max_age``. That eventual
consistency is fine for a public listing and is the point of the short TTL.

The payload is serialized exactly once per request: the same JSON bytes back both
the ETag and the response body.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import Request, Response

_DEFAULT_MAX_AGE = 30  # seconds — public list data is read-mostly


def _serialize(payload: Any) -> bytes:
    """Canonical JSON bytes, reused for the ETag and the body (one dumps/request)."""
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def _weak_etag(body: bytes) -> str:
    return 'W/"' + hashlib.blake2b(body, digest_size=16).hexdigest() + '"'


def _if_none_match(header: str | None, etag: str) -> bool:
    """RFC 7232 ``If-None-Match``: matches ``*``, or any tag in a comma-separated
    list, using weak comparison (the ``W/`` prefix is ignored on both sides)."""
    if not header:
        return False
    tags = [t.strip() for t in header.split(",") if t.strip()]
    if "*" in tags:
        return True
    opaque = etag.removeprefix("W/")
    return any(t.removeprefix("W/") == opaque for t in tags)


def conditional_json(request: Request, payload: Any, max_age: int = _DEFAULT_MAX_AGE) -> Response:
    """Serialize ``payload`` to JSON once, attach ``Cache-Control`` + ``ETag``, and
    return ``304 Not Modified`` (no body) when the client's ``If-None-Match`` matches."""
    body = _serialize(payload)
    etag = _weak_etag(body)
    headers = {"Cache-Control": f"public, max-age={max_age}", "ETag": etag}
    if _if_none_match(request.headers.get("if-none-match"), etag):
        return Response(status_code=304, headers=headers)
    return Response(content=body, media_type="application/json", headers=headers)
