from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.http_cache import conditional_json
from app.db.session import get_session
from app.schemas.review import ReviewForm
from app.services import review_service
from app.services.telegram_gateway import gateway
from app.ws.manager import manager

router = APIRouter(tags=["reviews"])


@router.get("/reviews")
def get_reviews(request: Request, site: str | None = None) -> Response:
    """Public reviews (cache-served, with ETag + max-age; 304 on If-None-Match)."""
    return conditional_json(request, review_service.get_public_reviews(site))


@router.post("/reviews")
async def submit_review(data: ReviewForm, session: AsyncSession = Depends(get_session)) -> dict:
    entry = await review_service.create_review(session, data)
    await manager.broadcast({
        "event": "new_review", "review_id": entry["id"], "userName": entry["userName"],
        "text": entry["text"], "site": entry["site"], "timestamp": entry["createdAt"],
    })
    await gateway.notify_new_review(entry["userName"], entry["text"])
    return {"status": "success", "id": entry["id"]}
