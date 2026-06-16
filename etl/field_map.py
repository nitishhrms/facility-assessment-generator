"""Central schema mapping — the Python twin of ``src/config/fieldMap.js``.

Every "messy CMS government field name -> clean report label" decision lives
here in one place so the rest of the pipeline never hard-codes raw column names.
"""

# CMS Provider Data Catalog dataset identifiers.
DATASETS = {
    "provider": "4pq5-n9py",  # Nursing Home Provider Information
    "claims": "ijh5-nb2v",    # Medicare Claims Quality Measures
    "averages": "xcdc-v8bm",  # State / US Averages
}

MEDICARE_BASE = "https://www.medicare.gov/care-compare/details/nursing-home"


def medicare_url(ccn: str, state: str = "") -> str:
    """Clickable Medicare Care Compare profile URL for a facility."""
    qs = f"?state={state}" if state else ""
    return f"{MEDICARE_BASE}/{ccn}/view-all{qs}"


# Star ratings: CMS field -> report label (rendered in this order).
RATING_FIELDS = [
    {"key": "overall_rating", "label": "Overall Star Rating"},
    {"key": "health_inspection_rating", "label": "Health Inspection"},
    {"key": "staffing_rating", "label": "Staffing"},
    {"key": "qm_rating", "label": "Quality of Resident Care"},
]

# The 12 hospitalization / ED metric lines come from 4 CMS claims measures.
# For each measure we emit facility value (claims dataset, `adjusted_score`) plus
# the national & state averages (averages dataset, `avg_column`).
# Per the brief: STR = Short-Stay, LT = Long-Stay.
CLAIMS_MEASURES = [
    {
        "code": "521",
        "group": "Short Stay",
        "short_name": "STR Hosp.",
        "facility_label": "Short Term Hospitalization",
        "national_label": "STR National Avg. for Hospitalization",
        "state_label": "STR State National Avg. for Hospitalization",
        "avg_column": "percentage_of_short_stay_residents_who_were_rehospitalized__1d02",
        "unit": "%",
        "decimals": 1,
    },
    {
        "code": "522",
        "group": "Short Stay",
        "short_name": "STR ED",
        "facility_label": "STR ED Visit",
        "national_label": "STR ED Visits National Avg.",
        "state_label": "STR ED Visits State Avg.",
        "avg_column": "percentage_of_short_stay_residents_who_had_an_outpatient_em_d911",
        "unit": "%",
        "decimals": 1,
    },
    {
        "code": "551",
        "group": "Long Stay",
        "short_name": "LT Hosp.",
        "facility_label": "LT Hospitalization",
        "national_label": "LT National Avg. for Hospitalization",
        "state_label": "LT State National Avg. for Hospitalization",
        "avg_column": "number_of_hospitalizations_per_1000_longstay_resident_days",
        "unit": "",
        "decimals": 2,
    },
    {
        "code": "552",
        "group": "Long Stay",
        "short_name": "LT ED",
        "facility_label": "ED Visit",
        "national_label": "LT ED Visits National Avg.",
        "state_label": "LT ED Visits State Avg.",
        "avg_column": "number_of_outpatient_emergency_department_visits_per_1000_l_de9d",
        "unit": "",
        "decimals": 2,
    },
]
