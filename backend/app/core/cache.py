"""In-memory read cache for the hot public endpoints.

The candidate sites poll ``/jobs``, ``/categories`` and ``/reviews`` constantly.
Serving those from a process-local cache (refreshed at startup, mutated in place
on every write) keeps reads off the database entirely — the web-performance
optimization the platform leans on. Writes update both the DB (source of truth)
and this cache, so the cache is never stale after a successful write.

This is deliberately a simple module-level singleton: there is exactly one cache
per process and it holds already-serialized public dicts (not ORM objects).
"""

from __future__ import annotations

from typing import Any


class AppCache:
    jobs: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    categories: list[dict[str, Any]] = []
    db_ready: bool = False  # True once startup DB init + warm-up succeeds

    # ── Jobs (ordered newest-first) ───────────────────────────────────────────
    @classmethod
    def set_jobs(cls, jobs: list[dict[str, Any]]) -> None:
        cls.jobs = jobs

    @classmethod
    def insert_job(cls, entry: dict[str, Any]) -> None:
        cls.jobs.insert(0, entry)

    @classmethod
    def replace_job(cls, entry: dict[str, Any]) -> bool:
        """Replace a job in place, preserving created_at/image_url. False on miss."""
        for i, job in enumerate(cls.jobs):
            if job["id"] == entry["id"]:
                entry["created_at"] = job.get("created_at")
                entry.setdefault("image_url", job.get("image_url"))
                cls.jobs[i] = entry
                return True
        return False

    @classmethod
    def set_job_image(cls, job_id: str, image_url: str) -> None:
        for job in cls.jobs:
            if job["id"] == str(job_id):
                job["image_url"] = image_url
                break

    @classmethod
    def remove_job(cls, job_id: str) -> None:
        job_id = str(job_id)
        cls.jobs = [j for j in cls.jobs if j["id"] != job_id]

    # ── Reviews ───────────────────────────────────────────────────────────────
    @classmethod
    def set_reviews(cls, reviews: list[dict[str, Any]]) -> None:
        cls.reviews = reviews

    @classmethod
    def insert_review(cls, entry: dict[str, Any]) -> None:
        cls.reviews.insert(0, entry)

    # ── Categories ────────────────────────────────────────────────────────────
    @classmethod
    def set_categories(cls, categories: list[dict[str, Any]]) -> None:
        cls.categories = categories

    @classmethod
    def has_category(cls, cat_id: str) -> bool:
        return any(c.get("id") == cat_id for c in cls.categories)
