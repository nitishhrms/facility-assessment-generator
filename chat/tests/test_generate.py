"""Phase 3 tests — generation prompt-building + parsing (pure, offline, no API)."""

from types import SimpleNamespace

from chat.generate import (
    WEB_SEARCH_TOOL,
    answer_text,
    build_request,
    format_context,
    rag_citations,
    web_citations,
)

_CTX = [
    {"pmid": "1", "section": "RESULTS", "text": "Finding one.", "source_url": "u1"},
    {"pmid": "1", "section": "BACKGROUND", "text": "Finding two.", "source_url": "u1"},
    {"pmid": "2", "section": "METHODS", "text": "Finding three.", "source_url": "u2"},
]


def test_format_context_numbers_and_tags():
    out = format_context(_CTX)
    assert "[1] (PMID 1, RESULTS) Finding one." in out
    assert "[3] (PMID 2, METHODS) Finding three." in out


def test_format_context_empty():
    assert format_context([]) == "(no excerpts retrieved)"


def test_build_request_rag_has_no_tools_and_embeds_context():
    req = build_request("does X cause Y?", "rag", _CTX)
    assert "tools" not in req
    assert req["thinking"] == {"type": "adaptive"}
    assert req["model"].startswith("claude-opus-4-8")
    user = req["messages"][0]["content"]
    assert "does X cause Y?" in user
    assert "PMID 1" in user                      # context inlined


def test_build_request_web_adds_search_tool_and_bare_query():
    req = build_request("latest 2025 guidelines?", "web")
    assert req["tools"] == [WEB_SEARCH_TOOL]
    assert req["messages"][0]["content"] == "latest 2025 guidelines?"  # no context block


def test_answer_text_joins_only_text_blocks():
    msg = SimpleNamespace(content=[
        SimpleNamespace(type="thinking", thinking="(hidden)"),
        SimpleNamespace(type="text", text="Hello "),
        SimpleNamespace(type="text", text="world."),
    ])
    assert answer_text(msg) == "Hello world."


def test_rag_citations_dedupe_by_pmid():
    cits = rag_citations(_CTX)
    assert [c["pmid"] for c in cits] == ["1", "2"]   # pmid 1 deduped
    assert cits[0]["source_url"] == "u1"


def test_web_citations_from_tool_result_and_text_blocks():
    msg = SimpleNamespace(content=[
        SimpleNamespace(type="web_search_tool_result", content=[
            SimpleNamespace(url="https://a.org", title="A"),
            SimpleNamespace(url="https://b.org", title="B"),
        ]),
        SimpleNamespace(type="text", text="answer",
                        citations=[SimpleNamespace(url="https://a.org", title="A")]),  # dup
    ])
    cits = web_citations(msg)
    assert [c["url"] for c in cits] == ["https://a.org", "https://b.org"]  # deduped
