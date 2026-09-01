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


def test_build_icsr_reads_nested_patient_and_drug():
    report = {
        "worldwide_unique_id": "NESTED-123",
        "product_name": "Aspirin",
        "reaction_meddra_term": "Headache",
        "reaction_pt_code": "10012345",
        "reaction_pt_name": "Headache",
        "first_received_date": date(2023, 1, 1),
        "patient": {"identifier": "PAT-1", "sex": "male", "age": 30},
        "drug": {
            "name": "Aspirin",
            "dose_text": "100 mg",
            "route_of_administration": "oral",
            "batch_number": "BATCH-1",
            "indication": "pain",
            "action_taken": "withdrawn",
            "therapy_start_date": date(2022, 12, 31),
            "therapy_end_date": date(2023, 1, 1),
        },
        "reporter_name": "Dr Foo",
        "reporter_qualification": "physician",
        "reporter_country": "US",
    }
    xml = pv_e2b.build_icsr(report, sender_id="SENDER", receiver_id="RECEIVER")
    assert "PAT-1" in xml
    assert "Aspirin" in xml
    assert "10012345" in xml
    assert "100 mg" in xml
