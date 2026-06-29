from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class StaffLogin(BaseModel):
    username: str
    password: str


class StaffCreate(BaseModel):
    username: str
    password: str
    role: str  # "admin" | "worker"
    full_name: str | None = None


class CandidateRegister(BaseModel):
    email: str
    password: str
    full_name: str
    birthdate: date  # ISO YYYY-MM-DD; 18+ enforced server-side


class CandidateLogin(BaseModel):
    email: str
    password: str


class GoogleLogin(BaseModel):
    id_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str | None = None
    username: str | None = None
    full_name: str | None = None
    email: str | None = None
