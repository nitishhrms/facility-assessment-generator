"""Tiny in-memory CMS payloads for offline, deterministic tests."""

PROVIDER = {
    "cms_certification_number_ccn": "686123",
    "provider_name": "Kendall Lakes Healthcare And Rehab Center",
    "provider_address": "9275 SW 152nd St",
    "citytown": "Miami",
    "state": "FL",
    "zip_code": "33176",
    "number_of_certified_beds": "150",
    "overall_rating": "5",
    "health_inspection_rating": "4",
    "staffing_rating": "5",
    "qm_rating": "3",
    "processing_date": "2026-05-01",
}

CLAIMS = [
    {"measure_code": "521", "adjusted_score": "20.0"},   # vs national 22.0 -> better
    {"measure_code": "522", "adjusted_score": "13.0"},   # vs national 12.0 -> worse
    {"measure_code": "551", "adjusted_score": "1.50"},   # vs national 1.60 -> better
    {"measure_code": "552", "adjusted_score": "1.10"},   # vs national 1.00 -> worse
]

AVERAGES = [
    {
        "state_or_nation": "NATION",
        "processing_date": "2026-05-01",
        "percentage_of_short_stay_residents_who_were_rehospitalized__1d02": "22.0",
        "percentage_of_short_stay_residents_who_had_an_outpatient_em_d911": "12.0",
        "number_of_hospitalizations_per_1000_longstay_resident_days": "1.60",
        "number_of_outpatient_emergency_department_visits_per_1000_l_de9d": "1.00",
    },
    {
        "state_or_nation": "FL",
        "percentage_of_short_stay_residents_who_were_rehospitalized__1d02": "21.0",
        "percentage_of_short_stay_residents_who_had_an_outpatient_em_d911": "11.5",
        "number_of_hospitalizations_per_1000_longstay_resident_days": "1.55",
        "number_of_outpatient_emergency_department_visits_per_1000_l_de9d": "1.05",
    },
]
