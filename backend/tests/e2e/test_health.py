def test_health_reports_ready(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["db_ready"] is True
    assert body["status"] == "ok"
