from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.rate_limit import limiter
from app.schemas.ai import AiChatForm
from app.services.ai import service as ai_service

router = APIRouter(tags=["ai"])


@router.post("/ai/chat")
@limiter.limit("15/minute")
async def ai_chat(request: Request, form: AiChatForm) -> dict:
    """Thin, rate-limited proxy to the configured AI provider. Jobs context comes
    from the client, so this route never touches the database."""
    return {"reply": await ai_service.chat(form)}
