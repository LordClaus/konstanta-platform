"""Cross-cutting HTTP middleware.

* :class:`RequestContextMiddleware` — gives every request a correlation id
  (honoring an inbound ``X-Request-ID``), echoes it back on the response, and
  logs one access line with the status and duration. The id is also exposed via a
  :class:`~contextvars.ContextVar` so any log emitted while handling the request
  can be tied back to it.
* :class:`SecurityHeadersMiddleware` — adds a few conservative security headers
  to every response.

Both pass non-HTTP scopes (e.g. WebSocket) straight through.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = logging.getLogger("api.request")

#: correlation id of the in-flight request ("-" outside a request)
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

_HEADER = "X-Request-ID"

_Next = Callable[[Request], Awaitable[Response]]


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: _Next) -> Response:
        rid = request.headers.get(_HEADER) or uuid.uuid4().hex[:12]
        token = request_id_ctx.set(rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000
            log.exception("%s %s -> ERROR in %.1fms [%s]",
                          request.method, request.url.path, elapsed, rid)
            raise
        else:
            elapsed = (time.perf_counter() - start) * 1000
            response.headers[_HEADER] = rid
            log.info("%s %s -> %s in %.1fms [%s]",
                     request.method, request.url.path, response.status_code, elapsed, rid)
            return response
        finally:
            request_id_ctx.reset(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: _Next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response
