"""Google Gemini provider (generativelanguage REST API)."""

from __future__ import annotations

import logging

import aiohttp

from app.config import get_settings
from app.schemas.ai import AiMessage
from app.services.ai.base import AIProvider, AIProviderError

log = logging.getLogger("api.ai.gemini")


class GeminiProvider(AIProvider):
    name = "gemini"

    @property
    def available(self) -> bool:
        return bool(get_settings().gemini_api_key)

    async def complete(self, system: str, messages: list[AiMessage]) -> str:
        s = get_settings()
        contents = [
            {"role": "user" if m.role == "user" else "model", "parts": [{"text": m.content[:2000]}]}
            for m in messages
        ]
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {"maxOutputTokens": 600, "temperature": 0.4},
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{s.gemini_model}:generateContent"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, params={"key": s.gemini_api_key}, json=payload,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        log.warning("Gemini error %s: %s", resp.status, str(data)[:300])
                        raise AIProviderError("upstream error")
        except TimeoutError as exc:
            raise AIProviderError("timeout") from exc
        except aiohttp.ClientError as exc:
            log.warning("Gemini call failed: %s", exc)
            raise AIProviderError("unavailable") from exc

        try:
            return (data["candidates"][0]["content"]["parts"][0]["text"] or "").strip()
        except (KeyError, IndexError, TypeError):
            return ""
