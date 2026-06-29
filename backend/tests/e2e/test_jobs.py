def _job_payload() -> dict:
    return {
        "title_ua": "Зварювальник", "title_cz": "Svářeč", "title_en": "Welder",
        "type": "Factory", "salary": "40000 Kč", "is_new": True,
        "sites": ["konstanta"],
        "cities": [{"name": "Brno", "housing": True}, {"name": "Praha", "housing": False}],
    }


def test_job_crud_and_site_placement(client, admin_headers):
    jid = client.post("/jobs", headers=admin_headers, json=_job_payload()).json()["id"]

    # Visible on its assigned site; location derived from city names.
    konstanta = client.get("/jobs", params={"site": "konstanta"}).json()
    mine = next(j for j in konstanta if j["id"] == jid)
    assert mine["location"] == "Brno, Praha"
    assert mine["cities"][0] == {"name": "Brno", "housing": True}
    assert "konstanta" in mine["sites"]

    # Not visible on the other site (sites == ["konstanta"]).
    robota = client.get("/jobs", params={"site": "robota"}).json()
    assert all(j["id"] != jid for j in robota)

    # Clearing sites makes it visible everywhere.
    upd = {**_job_payload(), "sites": []}
    assert client.put(f"/jobs/{jid}", headers=admin_headers, json=upd).status_code == 200
    robota = client.get("/jobs", params={"site": "robota"}).json()
    assert any(j["id"] == jid for j in robota)

    # Delete is idempotent-safe: second delete → 404.
    assert client.delete(f"/jobs/{jid}", headers=admin_headers).status_code == 200
    assert client.delete(f"/jobs/{jid}", headers=admin_headers).status_code == 404


def test_create_job_requires_admin(client):
    assert client.post("/jobs", json=_job_payload()).status_code in (401, 403)
