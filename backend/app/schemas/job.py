from __future__ import annotations

from pydantic import BaseModel


class CityItem(BaseModel):
    name: str
    housing: bool = False


class JobForm(BaseModel):
    title_ua: str
    title_cz: str
    title_en: str
    type: str  # category id
    location: str | None = None  # legacy single-location; derived from cities if omitted
    salary: str | None = None
    description: str | None = None
    is_new: bool = True
    sites: list[str] = []  # candidate sites to publish on; [] = everywhere
    cities: list[CityItem] = []
