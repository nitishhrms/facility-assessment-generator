"""Unit tests for the pure transform/validation core (no network, no DB)."""

from etl.tests.fixtures import AVERAGES, CLAIMS, PROVIDER
from etl.transform import build_report, data_quality, verdict_vs


def test_verdict_vs_lower_is_better():
    assert verdict_vs(20.0, 22.0) == "better"
    assert verdict_vs(13.0, 12.0) == "worse"
    assert verdict_vs(5.0, 5.0) == "same"
    assert verdict_vs(None, 5.0) == "na"


def test_build_report_core_fields():
    report = build_report(PROVIDER, CLAIMS, AVERAGES)
    assert report["ccn"] == "686123"
    assert report["state"] == "FL"
    assert report["name"] == "Kendall Lakes Healthcare And Rehab Center"
    assert report["location"] == "9275 SW 152nd St, Miami, FL 33176"
    assert report["certified_beds"] == 150
    assert report["medicare_url"].endswith("/686123/view-all?state=FL")


def test_name_override_wins():
    report = build_report(PROVIDER, CLAIMS, AVERAGES, {"override_name": "Custom Name"})
    assert report["name"] == "Custom Name"
    assert report["official_name"] == "Kendall Lakes Healthcare And Rehab Center"


def test_metric_verdicts_against_national():
    report = build_report(PROVIDER, CLAIMS, AVERAGES)
    by_code = {m["code"]: m for m in report["metrics"]}
    assert by_code["521"]["verdict_national"] == "better"
    assert by_code["522"]["verdict_national"] == "worse"
    assert by_code["551"]["verdict_national"] == "better"
    assert by_code["552"]["verdict_national"] == "worse"


def test_qa_summary_counts():
    report = build_report(PROVIDER, CLAIMS, AVERAGES)
    # 2 of 4 measures at or better than national.
    assert report["qa_summary"].startswith("2 of 4")


def test_data_quality_complete():
    report = build_report(PROVIDER, CLAIMS, AVERAGES)
    dq = data_quality(report)
    assert dq["completeness"] == 100
    assert dq["status"] == "complete"
    assert dq["missing"] == []


def test_data_quality_flags_missing_rating():
    provider = dict(PROVIDER)
    provider["staffing_rating"] = ""  # simulate a missing CMS field
    report = build_report(provider, CLAIMS, AVERAGES)
    dq = data_quality(report)
    assert dq["status"] == "partial"
    assert "Staffing" in dq["missing"]
    assert dq["completeness"] < 100


def test_build_report_none_provider():
    assert build_report(None, [], []) is None
