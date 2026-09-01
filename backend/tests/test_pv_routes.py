"""Integration tests for the pharmacovigilance API."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app
from app.services import dossier_service, llm
from app.services.dossier_service import create_dossier


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(dossier_service, "_DOSSIERS_ROOT", tmp_path)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def dossier_id(client):
    return create_dossier("PV Test")["id"]


def valid_report_payload():
    return {
        "product_name": "Aspirin",
        "reaction_meddra_term": "Headache",
        "reaction_description": "Severe headache began two hours after dose.",
        "patient": {"identifier": "PAT-1", "age": 30, "sex": "male"},
        "reporter_name": "Dr Foo",
        "reporter_email": "reporter@example.com",
        "reporter_organisation": "Example Clinic",
        "drug": {
            "name": "Aspirin",
            "dose_text": "100 mg",
            "route_of_administration": "oral",
        },
    }


def test_report_roundtrip_and_minimum_criteria(client, dossier_id):
    response = client.post(
        f"/api/v1/dossiers/{dossier_id}/pv/reports", json=valid_report_payload()
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["worldwide_unique_id"]
    assert report["first_received_date"]

    check = client.get(
        f"/api/v1/dossiers/{dossier_id}/pv/reports/{report['report_id']}/minimum-criteria"
    )
    assert check.status_code == 200
    data = check.json()
    assert data["patient"] is True
    assert data["reporter"] is True
    assert data["product"] is True
    assert data["reaction"] is True
    assert data["missing"] == []


def test_meddra_confirm_updates_report_coding(client, dossier_id, monkeypatch):
    report = client.post(
        f"/api/v1/dossiers/{dossier_id}/pv/reports", json=valid_report_payload()
    ).json()

    async def fake_generate_json(prompt, max_tokens=None):
        return json.dumps({"pt_code": "10012345", "pt_name": "Headache"})

    monkeypatch.setattr(llm, "generate_json", fake_generate_json)

    suggest = client.post(
        f"/api/v1/dossiers/{dossier_id}/pv/meddra/suggest", params={"term": "Headache"}
    )
    assert suggest.status_code == 200
    assert suggest.json()["pt_code"] == "10012345"

    confirmed = client.put(
        f"/api/v1/dossiers/{dossier_id}/pv/meddra/confirm",
        params={"report_id": report["report_id"], "term": "Headache"},
    )
    assert confirmed.status_code == 200, confirmed.text
    data = confirmed.json()
    assert data["reaction_pt_code"] == "10012345"
    assert data["reaction_pt_name"] == "Headache"
    assert data["meddra"]["source"] == "user_confirmed"


def test_e2b_export_uses_persisted_report_shape(client, dossier_id, monkeypatch):
    report = client.post(
        f"/api/v1/dossiers/{dossier_id}/pv/reports", json=valid_report_payload()
    ).json()

    async def fake_generate_json(prompt, max_tokens=None):
        return json.dumps({"pt_code": "10012345", "pt_name": "Headache"})

    monkeypatch.setattr(llm, "generate_json", fake_generate_json)
    confirmed = client.put(
        f"/api/v1/dossiers/{dossier_id}/pv/meddra/confirm",
        params={"report_id": report["report_id"], "term": "Headache"},
    )
    assert confirmed.status_code == 200, confirmed.text

    response = client.get(
        f"/api/v1/dossiers/{dossier_id}/pv/reports/{report['report_id']}/e2b"
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/xml")
    assert b"10012345" in response.content
