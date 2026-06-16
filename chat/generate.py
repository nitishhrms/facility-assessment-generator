"""Answer generation — Claude Opus 4.8, grounded with citations.

The final stage of the pipeline. Two modes, selected by the router:

  - "rag" : answer a medical question using ONLY the compressed PubMed excerpts the
            retriever found, citing them inline as [PMID:xxxx]. Refuses cleanly when
            the context is insufficient — no fabrication, no individualized advice.
  - "web" : the corpus didn't cover the question (router T3), so Claude uses the
            server-side `web_search` tool to find current, reputable information.

Uses the official `anthropic` SDK with **streaming** (recommended for anything with
non-trivial output) and **adaptive thinking** (`{"type": "adaptive"}` — a fixed
`budget_tokens` is rejected on Opus 4.8). The API key is read server-side only, from
the environment / `.env` (never the browser, never committed).

Prompt building (`build_request`, `format_context`) and response parsing
(`answer_text`, `rag_citations`, `web_citations`) are pure and unit-test offline; only
`generate()` / `stream_generate()` touch the network, behind an injectable client.
"""

import os

# Model + decoding. Opus 4.8: adaptive thinking only; effort tunes depth/cost.
MODEL = os.environ.get("CHAT_MODEL", "claude-opus-4-8")
MAX_TOKENS = int(os.environ.get("CHAT_MAX_TOKENS", "2048"))
EFFORT = os.environ.get("CHAT_EFFORT", "medium")

# GA web-search server tool (dynamic filtering built in; no beta header needed).
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search"}

RAG_SYSTEM = (
    "You are a careful healthcare information assistant for the Medelite facility-"
    "quality context. Answer the user's question using ONLY the provided PubMed "
    "excerpts. Cite the excerpts you use inline as [PMID:<pmid>]. If the excerpts do "
    "not contain enough information to answer, say so plainly — do not invent facts. "
    "Give general, informational answers only; never individualized diagnosis, dosing, "
    "or treatment advice."
)

WEB_SYSTEM = (
    "You are a careful healthcare information assistant. The local knowledge base did "
    "not cover this question, so use the web_search tool to find current, reputable "
    "medical information, and cite the sources you used. Give general, informational "
    "answers only; never individualized diagnosis, dosing, or treatment advice."
)


def format_context(context) -> str:
    """Render compressed excerpts as a numbered, citable context block. Pure."""
    lines = []
    for i, c in enumerate(context or [], 1):
        tag = f"PMID {c.get('pmid', '?')}"
        section = c.get("section")
        if section:
            tag += f", {section}"
        lines.append(f"[{i}] ({tag}) {c.get('text', '').strip()}")
    return "\n".join(lines) if lines else "(no excerpts retrieved)"


def build_request(query: str, mode: str, context=None) -> dict:
    """Assemble the Messages API request kwargs for a mode. Pure."""
    if mode == "rag":
        system = RAG_SYSTEM
        user = f"Question: {query}\n\nContext excerpts:\n{format_context(context)}"
        tools = None
    else:  # "web"
        system = WEB_SYSTEM
        user = query
        tools = [WEB_SEARCH_TOOL]

    req = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": system,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": EFFORT},
        "messages": [{"role": "user", "content": user}],
    }
    if tools:
        req["tools"] = tools
    return req


def answer_text(message) -> str:
    """Concatenate the text blocks of a Claude message. Pure."""
    parts = [getattr(b, "text", "") for b in getattr(message, "content", [])
             if getattr(b, "type", None) == "text"]
    return "".join(parts).strip()


def rag_citations(context) -> list[dict]:
    """Citations for a RAG answer come from the excerpts we supplied. Pure."""
    seen, out = set(), []
    for c in context or []:
        pmid = c.get("pmid")
        if pmid and pmid not in seen:
            seen.add(pmid)
            out.append({"pmid": pmid, "source_url": c.get("source_url"),
                        "section": c.get("section")})
    return out


def web_citations(message) -> list[dict]:
    """Best-effort extraction of web_search sources from a Claude message. Pure."""
    seen, out = set(), []

    def add(url, title):
        if url and url not in seen:
            seen.add(url)
            out.append({"url": url, "title": title})

    for b in getattr(message, "content", []):
        btype = getattr(b, "type", None)
        if btype == "web_search_tool_result":
            for r in getattr(b, "content", None) or []:
                add(getattr(r, "url", None), getattr(r, "title", None))
        elif btype == "text":
            for cit in getattr(b, "citations", None) or []:
                add(getattr(cit, "url", None), getattr(cit, "title", None))
    return out


def _default_client():
    """Lazy Anthropic client; loads .env so ANTHROPIC_API_KEY is picked up server-side."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    import anthropic  # heavy import kept lazy
    return anthropic.Anthropic()


def generate(query: str, mode: str = "rag", context=None, client=None) -> dict:
    """Produce a grounded answer (non-streaming aggregate). Returns {answer, citations}."""
    client = client or _default_client()
    req = build_request(query, mode, context)
    with client.messages.stream(**req) as stream:   # stream avoids HTTP timeouts
        message = stream.get_final_message()
    return {
        "answer": answer_text(message),
        "citations": rag_citations(context) if mode == "rag" else web_citations(message),
        "mode": mode,
        "stop_reason": getattr(message, "stop_reason", None),
    }


def stream_generate(query: str, mode: str = "rag", context=None, client=None):
    """Yield answer text deltas, then a final {answer, citations} dict (for Phase 4 SSE)."""
    client = client or _default_client()
    req = build_request(query, mode, context)
    with client.messages.stream(**req) as stream:
        for text in stream.text_stream:
            yield {"type": "delta", "text": text}
        message = stream.get_final_message()
    yield {
        "type": "final",
        "answer": answer_text(message),
        "citations": rag_citations(context) if mode == "rag" else web_citations(message),
        "mode": mode,
        "stop_reason": getattr(message, "stop_reason", None),
    }
