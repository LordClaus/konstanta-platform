"""OpenAI Chat Completions provider.

Talks to the REST API directly over aiohttp (no SDK) to keep the dependency
surface and cold-start small — the call is a single POST, rate-limited and
time-boxed by the caller.
"""

from __future__ import annotations

import logging

import aiohttp

from app.config import get_settings
from app.schemas.ai import AiMessage
from app.services.ai.base import AIProvider, AIProviderError

log = logging.getLogger("api.ai.openai")

_ENDPOINT = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(AIProvider):
    name = "openai"

    @property
    def available(self) -> bool:
        return bool(get_settings().openai_api_key)

    async def complete(self, system: str, messages: list[AiMessage]) -> str:
        s = get_settings()
        payload = {
            "model": s.openai_model,
            "messages": [{"role": "system", "content": system}]
            + [
                {"role": "assistant" if m.role == "assistant" else "user", "content": m.content[:2000]}
                for m in messages
            ],
            "max_tokens": 600,
            "temperature": 0.4,
        }
        headers = {
            "Authorization": f"Bearer {s.openai_api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    _ENDPOINT, headers=headers, json=payload,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        log.warning("OpenAI error %s: %s", resp.status, str(data)[:300])
                        raise AIProviderError("upstream error")
        except TimeoutError as exc:
            raise AIProviderError("timeout") from exc
        except aiohttp.ClientError as exc:
            log.warning("OpenAI call failed: %s", exc)
            raise AIProviderError("unavailable") from exc

        try:
            return (data["choices"][0]["message"]["content"] or "").strip()
        except (KeyError, IndexError, TypeError):
            return ""
