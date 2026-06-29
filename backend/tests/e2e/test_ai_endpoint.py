def test_ai_chat_returns_503_when_unconfigured(client):
    # No OPENAI/GEMINI key in the test env → provider is None → 503.
    r = client.post("/ai/chat", json={"messages": [{"role": "user", "content": "hi"}], "lang": "en"})
    assert r.status_code == 503
