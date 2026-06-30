"""Conditional HTTP caching for the hot public read endpoints.

The job / category / review lists are read-mostly and already served from the
in-process :class:`AppCache` (no DB hit). This adds the HTTP layer on top: a short
``Cache-Control`` max-age plus a content ``ETag``, so browsers and any CDN/proxy
can revalidate cheaply — a request whose ``If-None-Match`` matches the current
ETag gets ``304 Not Modified`` with no body.

Writes mutate ``AppCache`` in place, so a changed payload yields a new ETag on the
very next read; downstream caches converge within ``max_age``. That eventual
consistency is fine for a public listing and is the point of the short TTL.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse

_DEFAULT_MAX_AGE = 30  # seconds — public list data is read-mostly


def compute_etag(payload: Any) -> str:
    """Weak ETag from the canonical JSON of ``payload`` (stable across requests)."""
    body = json.dumps(
        payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False, default=str
    ).encode("utf-8")
    return 'W/"' + hashlib.blake2b(body, digest_size=16).hexdigest() + '"'


def conditional_json(request: Request, payload: Any, max_age: int = _DEFAULT_MAX_AGE) -> Response:
    """Serialize ``payload`` as JSON with ``Cache-Control`` + ``ETag``, or return
    ``304 Not Modified`` when the client's ``If-None-Match`` already matches."""
    etag = compute_etag(payload)
    headers = {"Cache-Control": f"public, max-age={max_age}", "ETag": etag}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return JSONResponse(payload, headers=headers)
