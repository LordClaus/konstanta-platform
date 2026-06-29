from __future__ import annotations

from pydantic import BaseModel


class CategoryForm(BaseModel):
    label_ua: str
    label_cz: str
    label_en: str
