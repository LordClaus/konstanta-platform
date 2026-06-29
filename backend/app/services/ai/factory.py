"""Provider selection (Factory).

Returns the configured provider, transparently falling back to the other vendor
when the preferred one has no key. Returns ``None`` only when no provider is
configured at all (the chat endpoint then answers 503 and the widget hides).
"""

from __future__ import annotations

from app.config import get_settings
from app.services.ai.base import AIProvider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.openai_provider import OpenAIProvider

_REGISTRY: dict[str, AIProvider] = {
    "openai": OpenAIProvider(),
    "gemini": GeminiProvider(),
}


def get_provider() -> AIProvider | None:
    preferred = (get_settings().ai_provider or "openai").lower()
    chosen = _REGISTRY.get(preferred)
    if chosen and chosen.available:
        return chosen
    # Fall back to any other configured provider.
    for provider in _REGISTRY.values():
        if provider.available:
            return provider
    return None
