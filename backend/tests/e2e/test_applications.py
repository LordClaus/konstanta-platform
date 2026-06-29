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
