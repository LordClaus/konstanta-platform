"""AI provider contract (Strategy pattern).

The chat endpoint depends on this small interface, never on a concrete vendor.
Swapping OpenAI ↔ Gemini (or adding Anthropic later) is a new class + one factory
line — the router and service never change. This is the open/closed principle in
practice.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.ai import AiMessage


class AIProviderError(RuntimeError):
    """Raised by a provider on an upstream failure/timeout (mapped to 502/504)."""


class AIProvider(ABC):
    #: short identifier for logs/diagnostics
    name: str = "base"

    @property
    @abstractmethod
    def available(self) -> bool:
        """True when the provider has the credentials it needs to run."""

    @abstractmethod
    async def complete(self, system: str, messages: list[AiMessage]) -> str:
        """Return the assistant reply for ``messages`` under ``system`` guidance."""
