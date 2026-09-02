import pytest
from pathlib import Path

from app.services import db_repo, pv_expectedness

# Helper to create a temporary dossier with an expected-reactions record.
@pytest.fixture
def dossier_root(tmp_path: Path):
    expected = [
        {"pt_code": "10012345", "pt_name": "Headache"},
        {"pt_code": "10067890", "pt_name": "Nausea"},
    ]
    db_repo.feature_put(
        db_repo.dossier_id_from_root(tmp_path),
        "pv_expected_reactions", "expected_reactions", expected,
    )
    return tmp_path

def test_assess_expected(dossier_root):
    report = {
        "reaction_pt_code": "10012345",
        "is_serious": False,
    }
    result = pv_expectedness.assess(report, dossier_root)
    assert result["expectedness"] == "expected"
    assert not result["is_susar"]

def test_assess_unexpected_serious_fatal(dossier_root):
    report = {
        "reaction_pt_code": "99999999",
        "is_serious": True,
        "outcome": "fatal",
        "seriousness_criteria": [],
    }
    result = pv_expectedness.assess(report, dossier_root)
    assert result["expectedness"] == "unexpected"
    assert result["is_susar"]
    assert result["susar_due_days"] == 7
