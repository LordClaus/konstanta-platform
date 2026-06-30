from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.core.http_cache import conditional_json
from app.db.session import get_session
from app.schemas.category import CategoryForm
from app.services import category_service

router = APIRouter(tags=["categories"])


@router.get("/categories")
def get_categories(request: Request) -> Response:
    """Public category list ({id, label:{ua,cz,en}}) — drives site filters.
    Served with an ETag + max-age; a matching ``If-None-Match`` gets a 304."""
    return conditional_json(request, category_service.get_public_categories())


@router.post("/categories", dependencies=[Depends(require_role("admin"))])
async def create_category(data: CategoryForm, session: AsyncSession = Depends(get_session)) -> dict:
    cat_id = await category_service.create_category(session, data)
    return {"status": "success", "id": cat_id}


@router.put("/categories/{cat_id}", dependencies=[Depends(require_role("admin"))])
async def update_category(cat_id: str, data: CategoryForm,
                          session: AsyncSession = Depends(get_session)) -> dict:
    await category_service.update_category(session, cat_id, data)
    return {"status": "success", "id": cat_id}


@router.delete("/categories/{cat_id}", dependencies=[Depends(require_role("admin"))])
async def delete_category(cat_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    await category_service.delete_category(session, cat_id)
    return {"status": "success", "id": cat_id}
