"""Domain gate — is this a healthcare / facility question at all?

Runs after the security gate and before the router. Two stages, cheap -> expensive:

  1. Rule (fast accept): the query carries a healthcare/clinical keyword OR a
     facility/warehouse signal (CCN or a metric word, via `router.looks_structured`).
     The facility branch matters because structured questions like "rating for 015009"
     are in-domain yet score LOW against the PubMed medical corpus — the embedding
     backstop alone would wrongly reject them.
  2. Embedding backstop: for queries the rules don't catch, take the max cosine
     similarity to the corpus. Below `DOMAIN_FLOOR` -> out-of-domain -> polite refusal.

Out-of-domain is a refusal, NOT a web-search handoff (that distinction is the router's
T3, reserved for in-domain queries the corpus simply doesn't cover).

The rule classifier is pure and unit-tests offline; the embedding step uses the same
injectable `retrieve` seam as the router.
"""

import re

from chat.config import DOMAIN_FLOOR
from chat.router import default_retrieve, looks_structured

# Common clinical / healthcare vocabulary. Not exhaustive on purpose — niche medical
# phrasing is caught by the embedding backstop; this just short-circuits the obvious.
_HEALTHCARE_TERMS = [
    r"health\w*", r"medical", r"medicine", r"clinical", r"patients?", r"diseases?",
    r"diagnos\w*", r"treatments?", r"therap\w*", r"drugs?", r"medications?",
    r"symptoms?", r"infections?", r"cancer", r"tumou?rs?", r"surg\w*", r"nursing",
    r"hospitals?", r"facilit\w*", r"mortality", r"prognos\w*", r"syndromes?",
    r"chronic", r"acute", r"patholog\w*", r"genes?", r"proteins?", r"cells?",
    r"immun\w*", r"vaccines?", r"antibiotics?", r"dosages?", r"sepsis", r"diabetes",
    r"hypertension", r"cardiovascular", r"cardiac", r"neuro\w*", r"oncolog\w*",
    r"p?ediatric", r"geriatric", r"mitochondri\w*", r"metabolic", r"outcomes?",
]
_HEALTHCARE_RE = re.compile(r"\b(" + "|".join(_HEALTHCARE_TERMS) + r")\b", re.IGNORECASE)


def in_domain_rule(query: str) -> bool:
    """True when a rule clearly marks the query as healthcare/facility. Pure."""
    if looks_structured(query):          # facility/warehouse question (CCN or metric)
        return True
    return bool(_HEALTHCARE_RE.search(query))


def check(query, retrieve=None, floor: float = DOMAIN_FLOOR) -> dict:
    """Decide in/out of domain. Returns {in_domain, stage, top_similarity?, answer?}.

    `retrieve(query, k) -> list[hit dict]` is injectable for offline tests; defaults
    to real embedding + vector search.
    """
    if in_domain_rule(query):
        return {"in_domain": True, "stage": "rule", "top_similarity": None}

    retrieve = retrieve or default_retrieve
    hits = retrieve(query, 5)
    top = hits[0]["similarity"] if hits else 0.0
    if top >= floor:
        return {"in_domain": True, "stage": "embedding", "top_similarity": top}
    return {
        "in_domain": False,
        "stage": "embedding",
        "top_similarity": top,
        "answer": "I can only help with healthcare and facility-quality questions. "
                  "That looks outside my scope, so I can't answer it.",
    }


# --- Calibration probe (needs the model; run manually) -----------------------------

_IN_DOMAIN_PROBES = [
    "What are the risk factors for hospital-acquired sepsis?",
    "Does metabolic syndrome affect cardiovascular outcomes?",
    "How does programmed cell death work in plant tissues?",
]
_OUT_DOMAIN_PROBES = [
    "What stock should I buy this week?",
    "Who won the football match last night?",
    "Write me a poem about the ocean.",
]


def _probe() -> int:
    """Print max corpus similarity for in- vs out-of-domain probes to set DOMAIN_FLOOR."""
    def top_sim(q):
        hits = default_retrieve(q, 5)
        return hits[0]["similarity"] if hits else 0.0

    print("IN-DOMAIN (should be high):")
    for q in _IN_DOMAIN_PROBES:
        print(f"  {top_sim(q):.3f}  {q}")
    print("OUT-OF-DOMAIN (should be lower):")
    for q in _OUT_DOMAIN_PROBES:
        print(f"  {top_sim(q):.3f}  {q}")
    print(f"\nCurrent DOMAIN_FLOOR = {DOMAIN_FLOOR}")
    return 0


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Domain gate calibration probe.")
    ap.add_argument("--probe", action="store_true", help="Print probe similarities.")
    args = ap.parse_args()
    raise SystemExit(_probe() if args.probe else 0)
