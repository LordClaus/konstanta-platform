"""ORM → public-dict serializers.

The public API and the in-memory cache speak plain dicts (the shape the candidate
frontends expect), never ORM objects. Centralizing the mapping here keeps the
wire format identical whether a job comes from a fresh DB read or an in-place
cache mutation.
"""

from __future__ import annotations

from typing import Any

from app.core.constants import clean_cities, clean_sites, parse_cities
from app.models import Category, Job, Review
from app.schemas.job import JobForm


def job_location(data: JobForm, cities: list[dict[str, Any]]) -> str | None:
    """Single-location string: explicit ``location`` else joined city names."""
    return data.location or ", ".join(c["name"] for c in cities) or None


def job_to_public(job: Job) -> dict[str, Any]:
    return {
        "id": str(job.id),
        "title": {"ua": job.title_ua, "cz": job.title_cz, "en": job.title_en},
        "type": job.type,
        "category": job.type,  # alias: `type` is the filter category
        "location": job.location,
        "salary": job.salary,
        "description": job.description,
        "new": bool(job.is_new),
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "image_url": job.image_url,
        "sites": clean_sites(job.sites or []),
        "cities": parse_cities(job.cities or []),
    }


def job_form_to_public(job_id: str, data: JobForm, created_at: str | None,
                       image_url: str | None = None) -> dict[str, Any]:
    """Build a public job dict from a form (same shape as ``job_to_public``)."""
    cities = clean_cities(data.cities)
    return {
        "id": str(job_id),
        "title": {"ua": data.title_ua, "cz": data.title_cz, "en": data.title_en},
        "type": data.type,
        "category": data.type,
        "location": job_location(data, cities),
        "salary": data.salary,
        "description": data.description,
        "new": bool(data.is_new),
        "created_at": created_at,
        "image_url": image_url,
        "sites": clean_sites(data.sites),
        "cities": cities,
    }


def review_to_public(review: Review) -> dict[str, Any]:
    return {
        "id": str(review.id),
        "userName": review.user_name,
        "text": review.text,
        "rating": review.rating,
        "createdAt": review.created_at.isoformat() if review.created_at else None,
        "site": review.site,
    }


def category_to_public(category: Category) -> dict[str, Any]:
    return {
        "id": str(category.id),
        "label": {"ua": category.label_ua, "cz": category.label_cz, "en": category.label_en},
    }
