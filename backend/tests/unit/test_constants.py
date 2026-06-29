"""Unit tests for the pure helpers in app.core.constants."""

from __future__ import annotations

from app.core.constants import (
    clean_cities,
    clean_sites,
    normalize_lang,
    parse_cities,
    slug,
)


def test_slug_basic():
    assert slug("Heavy Industry") == "heavy-industry"
    assert slug("  Factory!! ") == "factory"


def test_slug_falls_back_for_non_ascii():
    # No ASCII letters/digits → random "cat-" prefix.
    assert slug("Завод").startswith("cat-")


def test_clean_sites_filters_and_dedupes():
    assert clean_sites(["konstanta", "robota", "konstanta", "bogus", ""]) == ["konstanta", "robota"]
    assert clean_sites(None) == []


def test_normalize_lang_defaults_to_ua():
    assert normalize_lang("cz") == "cz"
    assert normalize_lang("en") == "en"
    assert normalize_lang("xx") == "ua"
    assert normalize_lang(None) == "ua"


def test_clean_cities_drops_blanks_and_coerces_housing():
    out = clean_cities([{"name": "Praha", "housing": 1}, {"name": "  "}, {"name": "Brno"}])
    assert out == [{"name": "Praha", "housing": True}, {"name": "Brno", "housing": False}]


def test_parse_cities_tolerates_bad_json():
    assert parse_cities("not json") == []
    assert parse_cities('[{"name": "Plzeň", "housing": true}]') == [{"name": "Plzeň", "housing": True}]
    assert parse_cities([{"name": "Ostrava"}]) == [{"name": "Ostrava", "housing": False}]
