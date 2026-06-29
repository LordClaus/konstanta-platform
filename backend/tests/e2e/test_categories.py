def test_default_categories_are_seeded(client):
    r = client.get("/categories")
    assert r.status_code == 200
    ids = {c["id"] for c in r.json()}
    assert {"Factory", "Warehouse", "Cleaning", "Drivers"} <= ids


def test_category_crud_and_in_use_guard(client, admin_headers):
    labels = {"label_ua": "Будівництво", "label_cz": "Stavebnictví", "label_en": "Construction"}
    r = client.post("/categories", headers=admin_headers, json=labels)
    assert r.status_code == 200
    cid = r.json()["id"]
    assert cid == "construction"

    # Duplicate label → 409.
    assert client.post("/categories", headers=admin_headers, json=labels).status_code == 409

    # Update labels keeps the id.
    upd = {**labels, "label_ua": "Буд"}
    assert client.put(f"/categories/{cid}", headers=admin_headers, json=upd).status_code == 200

    # A job using the category blocks deletion (409) until reassigned.
    job = {"title_ua": "X", "title_cz": "X", "title_en": "X", "type": cid,
           "cities": [{"name": "Brno", "housing": False}]}
    jid = client.post("/jobs", headers=admin_headers, json=job).json()["id"]
    assert client.delete(f"/categories/{cid}", headers=admin_headers).status_code == 409

    client.delete(f"/jobs/{jid}", headers=admin_headers)
    assert client.delete(f"/categories/{cid}", headers=admin_headers).status_code == 200


def test_category_write_requires_admin(client):
    r = client.post("/categories", json={"label_ua": "a", "label_cz": "b", "label_en": "c"})
    assert r.status_code in (401, 403)
