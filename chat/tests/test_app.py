"""Phase 4 tests — FastAPI SSE framing with a stubbed pipeline (offline, no model/API)."""

import json

from fastapi.testclient import TestClient

from chat import app as app_module
from chat import pipeline


def _events(resp_text: str) -> list[dict]:
    return [json.loads(line[len("data:"):].strip())
            for line in resp_text.splitlines() if line.startswith("data:")]


def test_health():
    client = TestClient(app_module.app)
    assert client.get("/health").json() == {"status": "ok"}


def test_chat_streams_sse_events(monkeypatch):
    def fake_stream(message):
        yield {"type": "trace", "trace": {"router": {"tier": "T2", "top_similarity": 0.95}}}
        yield {"type": "delta", "text": "Hello "}
        yield {"type": "delta", "text": "world."}
        yield {"type": "final", "answer": "Hello world.", "tier": "T2",
               "source": "rag", "citations": [{"pmid": "1"}]}

    monkeypatch.setattr(pipeline, "stream", fake_stream)
    client = TestClient(app_module.app)
    resp = client.post("/chat", json={"message": "hi"})

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = _events(resp.text)
    assert [e["type"] for e in events] == ["trace", "delta", "delta", "final"]
    assert events[0]["trace"]["router"]["tier"] == "T2"
    assert "".join(e["text"] for e in events if e["type"] == "delta") == "Hello world."
    assert events[-1]["answer"] == "Hello world."
    assert events[-1]["citations"] == [{"pmid": "1"}]


def test_chat_requires_message_field():
    client = TestClient(app_module.app)
    assert client.post("/chat", json={}).status_code == 422  # pydantic validation
