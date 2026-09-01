import json
import pytest
from app.services import pv_expectedness, store_utils
from pathlib import Path

# Helper to create a temporary dossier root with expected reactions file.
@pytest.fixture
def dossier_root(tmp_path: Path):
    # create expected reactions JSON
    expected = [
        {"pt_code": "10012345", "pt_name": "Headache"},
        {"pt_code": "10067890", "pt_name": "Nausea"},
    ]
    (tmp_path / "pv").mkdir(parents=True)
    store_utils.write_json(tmp_path / "pv" / "expected_reactions.json", expected)
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
