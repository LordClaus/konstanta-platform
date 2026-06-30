"""E2E tests for job-alert subscriptions, including the HMAC-signed one-click
unsubscribe link (no login)."""

from app.services import notification_service


def test_subscribe_and_unsubscribe(client):
    email = "sub@example.com"
    assert client.post("/subscribe", json={"email": email, "category": "Factory"}).status_code == 200
    # Re-subscribing the same (recipient, category, site) tuple is deduped, still ok.
    assert client.post("/subscribe", json={"email": email, "category": "Factory"}).status_code == 200
    assert client.post("/unsubscribe", json={"email": email}).status_code == 200


def test_subscribe_requires_a_contact(client):
    assert client.post("/subscribe", json={}).status_code == 400


def test_subscribe_rejects_malformed_email(client):
    assert client.post("/subscribe", json={"email": "not-an-email"}).status_code == 400


def test_one_click_unsubscribe_validates_hmac(client):
    email = "alert@example.com"
    client.post("/subscribe", json={"email": email})

    good = client.get("/unsubscribe", params={"e": email, "k": notification_service.unsub_sig(email)})
    assert good.status_code == 200
    assert "unsubscrib" in good.text.lower()

    bad = client.get("/unsubscribe", params={"e": email, "k": "forged-signature"})
    assert bad.status_code == 200
    assert "invalid" in bad.text.lower()
