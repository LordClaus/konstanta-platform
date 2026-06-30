"""The public list endpoints advertise an ETag + Cache-Control and honor
conditional requests (If-None-Match → 304)."""


def test_public_lists_send_validators(client):
    for path in ("/jobs", "/categories", "/reviews"):
        r = client.get(path)
        assert r.status_code == 200
        assert r.headers.get("ETag")
        assert "max-age" in r.headers.get("Cache-Control", "")


def test_if_none_match_returns_304(client):
    first = client.get("/categories")
    etag = first.headers["ETag"]

    again = client.get("/categories", headers={"If-None-Match": etag})
    assert again.status_code == 304
    assert again.content == b""  # 304 carries no body
    assert again.headers.get("ETag") == etag


def test_changed_payload_invalidates_etag(client, admin_headers):
    before = client.get("/categories").headers["ETag"]

    labels = {"label_ua": "Логістика", "label_cz": "Logistika", "label_en": "Logistics"}
    cid = client.post("/categories", headers=admin_headers, json=labels).json()["id"]
    try:
        after = client.get("/categories").headers["ETag"]
        assert after != before  # a new category → a new validator
    finally:
        client.delete(f"/categories/{cid}", headers=admin_headers)
