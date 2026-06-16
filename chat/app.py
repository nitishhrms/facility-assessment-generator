"""FastAPI backend — the one place the Claude key lives.

Exposes `POST /chat`, which runs the full pipeline (security -> domain -> router ->
answer) and streams the result back as Server-Sent Events: a `trace` event (so the UI
can show which tier fired and the similarities), then answer `delta` events, then a
`final` event with citations. The React app talks only to this endpoint — the
`ANTHROPIC_API_KEY` is read server-side from `.env` and never reaches the browser.

Run locally:
    uvicorn chat.app:app --reload --port 8000
"""

import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from chat import pipeline

app = FastAPI(title="Medelite Healthcare RAG Chat", version="1.0")

# Allow the Vite dev server (any localhost port) to call the backend in development.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


def _sse(message: str):
    """Serialize pipeline events as an SSE byte stream."""
    for event in pipeline.stream(message):
        yield f"data: {json.dumps(event)}\n\n"


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _sse(req.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
