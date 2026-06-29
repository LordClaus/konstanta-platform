"""Unit tests for AI prompt assembly, provider selection, and the OpenAI
provider's payload building + transient-error retry policy."""

from __future__ import annotations

import asyncio

import pytest

from app.config import get_settings
from app.schemas.ai import AiChatForm, AiMessage
from app.services.ai import factory, service
from app.services.ai.base import AIProviderError
from app.services.ai.openai_provider import OpenAIProvider


async def _noop_sleep(*_args, **_kwargs):
    """Skip the retry backoff so the tests stay instant."""
    return None


def test_jobs_block_formats_and_caps():
    jobs = [{"title": "Welder", "type": "Factory", "location": "Brno", "salary": "40k"}]
    block = service._jobs_block(jobs)
    assert "Welder" in block and "[Factory]" in block and "Brno" in block


def test_jobs_block_empty():
    assert service._jobs_block([]) == "(no active vacancies provided)"


def test_build_system_prompt_includes_brand_and_jobs():
    form = AiChatForm(brand="Acme", lang="en", jobs=[{"title": "Driver"}], messages=[])
    prompt = service.build_system_prompt(form, "en")
    assert "Acme" in prompt
    assert "Driver" in prompt


def test_factory_prefers_configured_provider(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "ai_provider", "openai", raising=False)
    monkeypatch.setattr(s, "openai_api_key", "sk-test", raising=False)
    monkeypatch.setattr(s, "gemini_api_key", "", raising=False)
    assert factory.get_provider().name == "openai"


def test_factory_falls_back_to_available_provider(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "ai_provider", "openai", raising=False)
    monkeypatch.setattr(s, "openai_api_key", "", raising=False)
    monkeypatch.setattr(s, "gemini_api_key", "g-test", raising=False)
    assert factory.get_provider().name == "gemini"


def test_factory_returns_none_when_unconfigured(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "openai_api_key", "", raising=False)
    monkeypatch.setattr(s, "gemini_api_key", "", raising=False)
    assert factory.get_provider() is None


# ── OpenAI provider: payload + parsing ────────────────────────────────────────


def test_openai_payload_uses_configured_params_and_caps_input(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "openai_model", "gpt-4o-mini", raising=False)
    monkeypatch.setattr(s, "openai_max_tokens", 123, raising=False)
    monkeypatch.setattr(s, "openai_temperature", 0.9, raising=False)

    payload = OpenAIProvider()._build_payload("SYS", [AiMessage(role="user", content="x" * 5000)])

    assert payload["model"] == "gpt-4o-mini"
    assert payload["max_tokens"] == 123
    assert payload["temperature"] == 0.9
    assert payload["messages"][0] == {"role": "system", "content": "SYS"}
    assert len(payload["messages"][1]["content"]) == 2000  # long input is capped


def test_openai_extract_handles_happy_and_malformed():
    good = {"choices": [{"message": {"content": "  hi  "}}]}
    assert OpenAIProvider._extract(good) == "hi"
    assert OpenAIProvider._extract({}) == ""
    assert OpenAIProvider._extract({"choices": []}) == ""


# ── OpenAI provider: retry policy ─────────────────────────────────────────────


def _provider_with_responses(monkeypatch, responses: list):
    """An OpenAIProvider whose HTTP layer replays ``responses`` and never sleeps.
    Returns (provider, call_counter)."""
    s = get_settings()
    monkeypatch.setattr(s, "openai_api_key", "sk-test", raising=False)
    monkeypatch.setattr(asyncio, "sleep", _noop_sleep)
    provider = OpenAIProvider()
    calls = {"n": 0}

    async def fake_post_once(_payload, _headers, _timeout):
        calls["n"] += 1
        return responses.pop(0)

    monkeypatch.setattr(provider, "_post_once", fake_post_once)
    return provider, calls


async def test_openai_retries_once_on_transient_then_succeeds(monkeypatch):
    provider, calls = _provider_with_responses(
        monkeypatch, [(503, {}), (200, {"choices": [{"message": {"content": "ok"}}]})]
    )
    reply = await provider.complete("sys", [AiMessage(role="user", content="hi")])
    assert reply == "ok"
    assert calls["n"] == 2  # retried the 503, then succeeded


async def test_openai_does_not_retry_on_client_error(monkeypatch):
    provider, calls = _provider_with_responses(monkeypatch, [(400, {"error": "bad"})])
    with pytest.raises(AIProviderError):
        await provider.complete("sys", [AiMessage(role="user", content="hi")])
    assert calls["n"] == 1  # a 4xx is permanent — no retry


async def test_openai_gives_up_after_max_attempts_on_transient(monkeypatch):
    provider, calls = _provider_with_responses(monkeypatch, [(429, {}), (429, {})])
    with pytest.raises(AIProviderError):
        await provider.complete("sys", [AiMessage(role="user", content="hi")])
    assert calls["n"] == 2  # one retry, then give up
