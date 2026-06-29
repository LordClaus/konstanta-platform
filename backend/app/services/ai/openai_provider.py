"""OpenAI Chat Completions provider.

Talks to the REST API directly over aiohttp (no SDK) to keep the dependency
surface and cold-start small. The single POST is time-boxed by ``openai_timeout``
and retried once on a *transient* failure (429 / 5xx / timeout) with a short
backoff — those are the errors you actually hit against the OpenAI API under
load, and a single bounded retry smooths them over without risking a slow
request pile-up on the event loop. Generation params come from settings, so the
model/temperature/budget can be tuned per environment without a redeploy.
"""

from __future__ import annotations

import asyncio
import logging

import aiohttp

from app.config import get_settings
from app.schemas.ai import AiMessage
from app.services.ai.base import AIProvider, AIProviderError

log = logging.getLogger("api.ai.openai")

_ENDPOINT = "https://api.openai.com/v1/chat/completions"
_MAX_ATTEMPTS = 2  # first try + one retry
_BACKOFF_SECONDS = 0.5
_TRANSIENT_STATUSES = {429, 500, 502, 503, 504}
_MAX_MESSAGE_CHARS = 2000


class OpenAIProvider(AIProvider):
    name = "openai"

    @property
    def available(self) -> bool:
        return bool(get_settings().openai_api_key)

    def _build_payload(self, system: str, messages: list[AiMessage]) -> dict:
        """Assemble the Chat Completions body: system prompt first, then the
        capped conversation. Input is length-capped so one long paste can't blow
        the token budget (cost) or the latency."""
        s = get_settings()
        return {
            "model": s.openai_model,
            "messages": [{"role": "system", "content": system}]
            + [
                {
                    "role": "assistant" if m.role == "assistant" else "user",
                    "content": m.content[:_MAX_MESSAGE_CHARS],
                }
                for m in messages
            ],
            "max_tokens": s.openai_max_tokens,
            "temperature": s.openai_temperature,
        }

    async def _post_once(self, payload: dict, headers: dict, timeout: aiohttp.ClientTimeout) -> tuple[int, dict]:
        """One HTTP attempt → (status, json). Transport failures become a
        transient AIProviderError so the caller can decide whether to retry."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(_ENDPOINT, headers=headers, json=payload, timeout=timeout) as resp:
                    return resp.status, await resp.json()
        except TimeoutError as exc:
            raise AIProviderError("timeout") from exc
        except aiohttp.ClientError as exc:
            log.warning("OpenAI call failed: %s", exc)
            raise AIProviderError("unavailable") from exc

    async def complete(self, system: str, messages: list[AiMessage]) -> str:
        s = get_settings()
        payload = self._build_payload(system, messages)
        headers = {
            "Authorization": f"Bearer {s.openai_api_key}",
            "Content-Type": "application/json",
        }
        timeout = aiohttp.ClientTimeout(total=s.openai_timeout_seconds)

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            last = attempt == _MAX_ATTEMPTS
            try:
                http_status, data = await self._post_once(payload, headers, timeout)
            except AIProviderError:
                if last:
                    raise  # preserves the specific reason ("timeout"/"unavailable")
                await asyncio.sleep(_BACKOFF_SECONDS * attempt)
                continue

            if http_status == 200:
                return self._extract(data)

            log.warning("OpenAI HTTP %s (attempt %d): %s", http_status, attempt, str(data)[:300])
            if http_status not in _TRANSIENT_STATUSES or last:
                raise AIProviderError("upstream error")
            await asyncio.sleep(_BACKOFF_SECONDS * attempt)

        raise AIProviderError("unavailable")  # defensive; loop above always returns/raises

    @staticmethod
    def _extract(data: dict) -> str:
        """Pull the assistant text out of a Chat Completions response; an empty
        string lets the service substitute a localized fallback."""
        try:
            return (data["choices"][0]["message"]["content"] or "").strip()
        except (KeyError, IndexError, TypeError):
            return ""
