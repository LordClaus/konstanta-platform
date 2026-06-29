"""Unit tests for AI prompt assembly and provider selection."""

from __future__ import annotations

from app.config import get_settings
from app.schemas.ai import AiChatForm
from app.services.ai import factory, service


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
