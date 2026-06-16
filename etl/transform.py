"""TRANSFORM layer — the Python twin of ``src/lib/buildReport.js`` + ``dataQuality.js``.

Pure functions (no I/O) so they are trivial to unit-test. Merge the three CMS
payloads + optional manual inputs into ONE normalized report model, derive QA
benchmark verdicts, and compute a data-quality summary over the source data.
"""

from typing import Optional

from etl.field_map import CLAIMS_MEASURES, RATING_FIELDS, medicare_url

NA = "N/A"


def to_num(v) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fmt(v, decimals: int, unit: str = "") -> str:
    n = to_num(v)
    return NA if n is None else f"{n:.{decimals}f}{unit}"


def verdict_vs(facility: Optional[float], benchmark: Optional[float]) -> str:
    """Lower is better for hospitalization / ED measures."""
    if facility is None or benchmark is None:
        return "na"
    if facility < benchmark:
        return "better"
    if facility > benchmark:
        return "worse"
    return "same"


def compose_location(p: dict) -> str:
    city_state_zip = ", ".join(
        part
        for part in [
            p.get("citytown"),
            " ".join(x for x in [p.get("state"), p.get("zip_code")] if x),
        ]
        if part
    )
    composed = ", ".join(
        part for part in [p.get("provider_address"), city_state_zip] if part
    )
    return composed or p.get("location") or NA


def build_report(
    provider: Optional[dict],
    claims: list[dict],
    averages: list[dict],
    manual: Optional[dict] = None,
) -> Optional[dict]:
    """Merge CMS data + manual inputs into one normalized report model."""
    if not provider:
        return None
    manual = manual or {}

    state = provider.get("state") or ""
    ccn = provider.get("cms_certification_number_ccn") or ""

    official_name = provider.get("provider_name") or NA
    name = (manual.get("override_name") or "").strip() or official_name

    ratings = [
        {
            "label": f["label"],
            "value": to_num(provider.get(f["key"])),
            "text": str(provider[f["key"]]) if provider.get(f["key"]) else NA,
        }
        for f in RATING_FIELDS
    ]

    nation = next((r for r in averages if r.get("state_or_nation") == "NATION"), {})
    state_row = next((r for r in averages if r.get("state_or_nation") == state), {})
    claim_by_code = {c.get("measure_code"): c for c in claims}

    metrics = []
    for m in CLAIMS_MEASURES:
        facility_raw = (claim_by_code.get(m["code"]) or {}).get("adjusted_score")
        facility = to_num(facility_raw)
        national = to_num(nation.get(m["avg_column"]))
        state_val = to_num(state_row.get(m["avg_column"]))
        metrics.append(
            {
                "code": m["code"],
                "group": m["group"],
                "short_name": m["short_name"],
                "unit": m["unit"],
                "facility_label": m["facility_label"],
                "national_label": m["national_label"],
                "state_label": m["state_label"],
                "facility": facility,
                "national": national,
                "state": state_val,
                "facility_text": fmt(facility_raw, m["decimals"], m["unit"]),
                "national_text": fmt(nation.get(m["avg_column"]), m["decimals"], m["unit"]),
                "state_text": fmt(state_row.get(m["avg_column"]), m["decimals"], m["unit"]),
                "vs_national": None if (national is None or facility is None) else facility - national,
                "vs_state": None if (state_val is None or facility is None) else facility - state_val,
                "verdict_national": verdict_vs(facility, national),
                "verdict_state": verdict_vs(facility, state_val),
            }
        )

    scored = [m for m in metrics if m["verdict_national"] != "na"]
    better_or_same = len([m for m in scored if m["verdict_national"] != "worse"])
    qa_summary = (
        f"{better_or_same} of {len(scored)} hospitalization/ED measures "
        "at or better than the national average."
        if scored
        else "No hospitalization/ED benchmark data available for this facility."
    )

    table_rows = [
        ["Name of Facility", name],
        ["Location", compose_location(provider)],
        ["EMR", manual.get("emr") or NA],
        ["Census Capacity", provider.get("number_of_certified_beds") or NA],
        ["Current Census", manual.get("current_census") or NA],
        ["Type of Patient", manual.get("patient_type") or NA],
        ["Previous Coverage from Medelite", manual.get("previous_coverage") or NA],
        ["Previous Provider Performance from Medelite", manual.get("previous_performance") or NA],
        ["Medical Coverage", manual.get("medical_coverage") or NA],
        *[[r["label"], r["text"]] for r in ratings],
    ]
    for m in metrics:
        table_rows.append([m["facility_label"], m["facility_text"]])
        table_rows.append([m["national_label"], m["national_text"]])
        table_rows.append([m["state_label"], m["state_text"]])

    rating_map = {r["label"]: r["value"] for r in ratings}

    return {
        "ccn": ccn,
        "state": state,
        "name": name,
        "official_name": official_name,
        "location": compose_location(provider),
        "certified_beds": to_num(provider.get("number_of_certified_beds")),
        "medicare_url": medicare_url(ccn, state),
        "processing_date": provider.get("processing_date") or nation.get("processing_date"),
        "ratings": ratings,
        "rating_map": rating_map,
        "metrics": metrics,
        "qa_summary": qa_summary,
        "table_rows": table_rows,
    }


def data_quality(report: Optional[dict]) -> Optional[dict]:
    """Completeness / freshness / missing-field summary over the CMS-sourced fields."""
    if not report:
        return None

    cms_labels = [
        "Location",
        "Census Capacity",
        *[r["label"] for r in report["ratings"]],
    ]
    for m in report["metrics"]:
        cms_labels += [m["facility_label"], m["national_label"], m["state_label"]]

    value_by_label = {row[0]: row[1] for row in report["table_rows"]}
    checked = [
        {
            "label": label,
            "value": value_by_label.get(label),
            "ok": value_by_label.get(label) not in (None, NA),
        }
        for label in cms_labels
    ]

    populated = len([c for c in checked if c["ok"]])
    total = len(checked)
    missing = [c["label"] for c in checked if not c["ok"]]
    completeness = round((populated / total) * 100) if total else 0

    return {
        "populated": populated,
        "total": total,
        "completeness": completeness,
        "missing": missing,
        "processing_date": report.get("processing_date"),
        "status": "complete" if not missing else "partial",
    }
