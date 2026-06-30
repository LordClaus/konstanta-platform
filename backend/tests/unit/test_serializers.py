"""Unit tests for ORM → public-dict serializers (the wire contract)."""

from __future__ import annotations

from app.models import Category, Job, Review
from app.services import serializers


def test_job_to_public_shape_and_aliases():
    job = Job(
        id="j1", title_ua="UA", title_cz="CZ", title_en="EN", type="Factory",
        location="Brno", salary="40k", description="d", is_new=True,
        sites=["konstanta"], cities=[{"name": "Brno", "housing": True}],
    )
    pub = serializers.job_to_public(job)
    assert pub["id"] == "j1"
    assert pub["title"] == {"ua": "UA", "cz": "CZ", "en": "EN"}
    assert pub["type"] == "Factory"
    assert pub["category"] == "Factory"  # category is an alias of type
    assert pub["new"] is True
    assert pub["sites"] == ["konstanta"]
    assert pub["cities"] == [{"name": "Brno", "housing": True}]
    assert pub["created_at"] is None  # transient row → no timestamp


def test_job_to_public_drops_unknown_sites():
    job = Job(id="j2", title_ua="x", title_cz="x", title_en="x", type="Factory",
              sites=["konstanta", "bogus"], cities=[])
    assert serializers.job_to_public(job)["sites"] == ["konstanta"]


def test_review_to_public_shape():
    r = Review(id="r1", user_name="Bob", text="great", rating=5, site="robota")
    pub = serializers.review_to_public(r)
    assert pub["userName"] == "Bob"
    assert pub["text"] == "great"
    assert pub["rating"] == 5
    assert pub["site"] == "robota"


def test_category_to_public_shape():
    c = Category(id="factory", label_ua="Завод", label_cz="Továrna", label_en="Factory")
    pub = serializers.category_to_public(c)
    assert pub["id"] == "factory"
    assert pub["label"] == {"ua": "Завод", "cz": "Továrna", "en": "Factory"}
