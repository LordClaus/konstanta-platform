import uuid


def test_apply_then_my_applications(client):
    email = f"a{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post("/auth/register", json={
        "email": email, "password": "secret1", "full_name": "Appl Y", "birthdate": "1990-01-01"})
    token = reg.json()["access_token"]

    r = client.post("/apply", json={
        "name": "Appl Y", "phone": "+420123456", "email": email,
        "profession": "Welder", "lang": "ua"})
    assert r.status_code == 200

    r = client.get("/my-applications", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    apps = r.json()["applications"]
    assert apps and apps[0]["profession"] == "Welder"
    assert apps[0]["status"] == "received"  # internal "new" → candidate-facing "received"


def test_my_applications_requires_auth(client):
    assert client.get("/my-applications").status_code == 401


def test_sync_db_requires_staff(client):
    assert client.get("/sync-db").status_code in (401, 403)


def test_sync_db_pagination(client, admin_headers):
    for i in range(3):
        client.post("/apply", json={"name": f"Pager {i}", "phone": "+420555000"})

    page = client.get("/sync-db", params={"limit": 2}, headers=admin_headers)
    assert page.status_code == 200
    assert len(page.json()) <= 2

    # Out-of-range limit is rejected by validation.
    assert client.get("/sync-db", params={"limit": 0}, headers=admin_headers).status_code == 422
    assert client.get("/sync-db", params={"limit": 999}, headers=admin_headers).status_code == 422


def test_responses_carry_request_id_and_security_headers(client):
    r = client.get("/")
    assert r.headers.get("X-Request-ID")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
