"""Pipeline — orchestrates the whole chat turn.

Order (the brief's gate -> route -> respond):

    security gate ─► domain gate ─► intent router ─► dispatch
       │ block         │ refuse        T1 │ T2 │ T3
       ▼               ▼                  ▼    ▼    ▼
    safe refusal   polite refusal      SQL  RAG  web

Every stage is reached through an injectable seam, so this module unit-tests fully
offline with stubs — before `generate.py`/`compress.py` exist, and without loading the
embedding model or calling Claude. In production the seams default to the real
`security` / `domain` / `router` / `sql_answer` modules, with `compress` + `generate`
imported lazily for the T2/T3 answer.

Each turn returns one result dict carrying the `answer`, the `tier`/`source`, any
`citations`, and a `trace` of each stage's decision — that trace is what the SSE
backend (Phase 4) and React UI (Phase 5) surface so the system can "show its work".
"""

from chat import domain, router, security, sql_answer


def _citations(hits) -> list[dict]:
    """Unique source citations from retrieved hits, order-preserving."""
    seen, out = set(), []
    for h in hits or []:
        pmid = h.get("pmid")
        if pmid and pmid not in seen:
            seen.add(pmid)
            out.append({"pmid": pmid, "source_url": h.get("source_url"),
                        "year": h.get("year"), "final_decision": h.get("final_decision")})
    return out


def _result(answer, *, tier, source, trace, citations=None, rows=None, **extra) -> dict:
    out = {"answer": answer, "tier": tier, "source": source, "trace": trace,
           "citations": citations or [], "rows": rows or []}
    out.update(extra)
    return out


def _lazy_compress(query, hits):
    from chat.compress import shorten  # built next in Phase 3
    return shorten(query, hits)


def _lazy_generate(query, mode, context):
    from chat.generate import generate
    return generate(query, mode=mode, context=context)


def _lazy_stream_generate(query, mode, context):
    from chat.generate import stream_generate
    return stream_generate(query, mode=mode, context=context)


def _decide(query, security_check, domain_check, route):
    """Run the gates and router. Returns (early_result | None, decision | None, trace).

    `early_result` is a finished refusal (security/domain); when it's None, `decision`
    is the router's tier decision. Shared by `run()` and `stream()`.
    """
    trace = {}

    sec = security_check(query)
    trace["security"] = {key: sec.get(key) for key in ("safe", "stage", "category")}
    if not sec["safe"]:
        return (_result(sec["answer"], tier="blocked", source="refusal",
                        trace=trace, category=sec.get("category")), None, trace)

    dom = domain_check(query)
    trace["domain"] = {"in_domain": dom["in_domain"], "stage": dom["stage"],
                       "top_similarity": dom.get("top_similarity")}
    if not dom["in_domain"]:
        return (_result(dom["answer"], tier="out_of_domain", source="refusal",
                        trace=trace), None, trace)

    dec = route(query)
    trace["router"] = {"tier": dec["tier"], "source": dec["source"],
                       "top_similarity": dec.get("top_similarity")}
    return (None, dec, trace)


def run(query, *, security_check=None, domain_check=None, route=None,
        structured=None, compress_fn=None, generate_fn=None,
        retrieve=None, conn=None, k=5) -> dict:
    """Run one chat turn end-to-end and return the result + trace.

    All seams default to the real components; pass overrides to test offline. Each
    seam is called as a simple `fn(query)` (the `retrieve`/`k`/`conn` wiring is bound
    into the defaults below), except `structured(query, ccn)`, `compress_fn(query,
    hits)`, and `generate_fn(query, mode, context)`.
    """
    security_check = security_check or security.check
    domain_check = domain_check or (lambda q: domain.check(q, retrieve=retrieve))
    route = route or (lambda q: router.route(q, retrieve=retrieve, k=k))
    structured = structured or (lambda q, ccn: sql_answer.answer(q, ccn=ccn, conn=conn))
    compress_fn = compress_fn or _lazy_compress
    generate_fn = generate_fn or _lazy_generate

    # 1-3. Gates + router (shared with stream()).
    early, dec, trace = _decide(query, security_check, domain_check, route)
    if early is not None:
        return early

    # 4. Dispatch.
    if dec["tier"] == router.T1_STRUCTURED:
        out = structured(query, dec.get("ccn"))
        return _result(out["answer"], tier="T1", source="warehouse", trace=trace,
                       rows=out.get("rows"), kind=out.get("kind"))

    if dec["tier"] == router.T2_RAG:
        hits = dec.get("hits") or []
        shortened = compress_fn(query, hits)
        gen = generate_fn(query, mode="rag", context=shortened)
        return _result(gen["answer"], tier="T2", source="rag", trace=trace,
                       citations=gen.get("citations") or _citations(hits))

    # T3 — in-domain but uncovered: web search.
    gen = generate_fn(query, mode="web", context=None)
    return _result(gen["answer"], tier="T3", source="web", trace=trace,
                   citations=gen.get("citations") or [])


def stream(query, *, security_check=None, domain_check=None, route=None,
           structured=None, compress_fn=None, stream_fn=None,
           retrieve=None, conn=None, k=5):
    """Streaming variant of `run()` — yields SSE-ready events for one chat turn.

    Event shapes:
      {"type": "trace",  "trace": {...}}                 — emitted once, after routing
      {"type": "delta",  "text": "..."}                  — incremental answer text
      {"type": "final",  "answer", "tier", "source", "citations", "trace", ...}

    Refusals (security/domain) and T1 (SQL) answers are not token-streamed by Claude,
    so they arrive as a single delta + final. T2/T3 stream Claude's tokens via
    `stream_fn` (defaults to `generate.stream_generate`).
    """
    security_check = security_check or security.check
    domain_check = domain_check or (lambda q: domain.check(q, retrieve=retrieve))
    route = route or (lambda q: router.route(q, retrieve=retrieve, k=k))
    structured = structured or (lambda q, ccn: sql_answer.answer(q, ccn=ccn, conn=conn))
    compress_fn = compress_fn or _lazy_compress
    stream_fn = stream_fn or _lazy_stream_generate

    early, dec, trace = _decide(query, security_check, domain_check, route)
    yield {"type": "trace", "trace": trace}

    # Refusal (blocked / out-of-domain): single-shot answer.
    if early is not None:
        yield {"type": "delta", "text": early["answer"]}
        final = {"type": "final", "answer": early["answer"], "tier": early["tier"],
                 "source": early["source"], "citations": early.get("citations", []),
                 "trace": trace}
        if "category" in early:
            final["category"] = early["category"]
        yield final
        return

    # T1 structured: deterministic SQL answer, delivered whole.
    if dec["tier"] == router.T1_STRUCTURED:
        out = structured(query, dec.get("ccn"))
        yield {"type": "delta", "text": out["answer"]}
        yield {"type": "final", "answer": out["answer"], "tier": "T1",
               "source": "warehouse", "citations": [], "rows": out.get("rows") or [],
               "kind": out.get("kind"), "trace": trace}
        return

    # T2 RAG / T3 web: stream Claude's tokens.
    if dec["tier"] == router.T2_RAG:
        hits = dec.get("hits") or []
        context = compress_fn(query, hits)
        mode, fallback_citations = "rag", _citations(hits)
    else:
        context, mode, fallback_citations = None, "web", []

    final_event = None
    for ev in stream_fn(query, mode, context):
        if ev.get("type") == "delta":
            yield ev
        else:
            final_event = ev

    answer = (final_event or {}).get("answer", "")
    citations = (final_event or {}).get("citations") or fallback_citations
    yield {"type": "final", "answer": answer, "tier": dec["tier"],
           "source": dec["source"], "citations": citations, "trace": trace}
