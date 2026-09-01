import pytest
from app.services import pv_e2b
from datetime import date

def minimal_report():
    return {
        "worldwide_unique_id": "ABC-123",
        "product_name": "Aspirin",
        "reaction_meddra_term": "Headache",
        "reaction_pt_code": "10012345",
        "reaction_pt_name": "Headache",
        "first_received_date": date(2023, 1, 1),
        "case_report_type": "initial",
        "case_version": 1,
        "patient_identifier": "PAT-1",
        "patient_sex": "male",
        "patient_age": 30,
        "reporter_name": "Dr Foo",
        "reporter_qualification": "physician",
        "reporter_country": "US",
    }

def test_build_icsr_success():
    report = minimal_report()
    xml = pv_e2b.build_icsr(report, sender_id="SENDER", receiver_id="RECEIVER")
    assert "<id extension=\"ABC-123\"" in xml
    assert "Headache" in xml

def test_validate_missing_product():
    report = minimal_report()
    report.pop("product_name")
    problems = pv_e2b.validate(report)
    assert any("No suspect product" in p for p in problems)
