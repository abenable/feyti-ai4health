import pytest
from app.services import pv_minimum_criteria

def test_criteria_all_present():
    source = {
        "patient_identifier": "123",
        "reporter_name": "Dr Foo",
        "product_name": "Aspirin",
        "reaction_meddra_term": "Headache",
    }
    assert pv_minimum_criteria.is_valid_icsr(source)
    assert pv_minimum_criteria.missing_criteria(source) == []
    assert pv_minimum_criteria.describe_missing(source) == ""

def test_missing_patient():
    source = {
        "reporter_name": "Dr Foo",
        "product_name": "Aspirin",
        "reaction_meddra_term": "Headache",
    }
    assert not pv_minimum_criteria.is_valid_icsr(source)
    missing = pv_minimum_criteria.missing_criteria(source)
    assert missing == ["patient"]
    assert "identifiable patient" in pv_minimum_criteria.describe_missing(source)
