import uuid
from datetime import date


def _email() -> str:
    return f"u{uuid.uuid4().hex[:8]}@example.com"


def test_register_login_me_flow(client):
    email = _email()
    body = {"email": email, "password": "secret1", "full_name": "Test User", "birthdate": "1990-01-01"}

    r = client.post("/auth/register", json=body)
    assert r.status_code == 200 and r.json()["access_token"]

    # Duplicate registration → 409.
    assert client.post("/auth/register", json=body).status_code == 409

    # Login + profile.
    token = client.post("/auth/login", json={"email": email, "password": "secret1"}).json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == email

    # Wrong password → 401.
    assert client.post("/auth/login", json={"email": email, "password": "nope"}).status_code == 401


def test_register_minor_is_rejected(client):
    today = date.today()
    body = {"email": _email(), "password": "secret1", "full_name": "Kid",
            "birthdate": f"{today.year - 10:04d}-01-01"}
    assert client.post("/auth/register", json=body).status_code == 400
