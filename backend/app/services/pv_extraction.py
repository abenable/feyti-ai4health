"""Source-document extraction for ADR reports.

LLM extraction is preferred for free-form CIOMS/ADR text. If the model is
unavailable or returns unusable JSON, a deterministic label parser fills only
values explicitly present in the source; no fields are inferred.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.models.pv_schemas import PVDrugDraft, PVPatientDraft, PVReportDraft
from app.services import llm
from app.services.dossier_service import read_context

_SEVERITY_ALIASES = {
    "mild": "mild",
    "moderate": "moderate",
    "severe": "severe",
    "serious": "severe",
    "life-threatening": "life_threatening",
    "life threatening": "life_threatening",
    "fatal": "fatal",
}
_CAUSALITY_ALIASES = {
    "certain": "certain",
    "definitely related": "certain",
    "probable": "probable",
    "probably related": "probable",
    "possible": "possible",
    "possibly related": "possible",
    "unlikely": "unlikely",
    "unrelated": "unlikely",
    "conditional": "conditional",
    "unassessable": "unassessable",
}
_OUTCOME_ALIASES = {
    "recovered": "recovered",
    "resolved": "recovered",
    "recovering": "recovering",
    "resolving": "recovering",
    "not recovered": "not_recovered",
    "not resolved": "not_recovered",
    "fatal": "fatal",
    "died": "fatal",
    "death": "fatal",
    "unknown": "unknown",
}
_ACTION_ALIASES = {
    "withdrawn": "withdrawn",
    "drug withdrawn": "withdrawn",
    "dose reduced": "dose_reduced",
    "dose increased": "dose_increased",
    "dose not changed": "dose_not_changed",
    "not applicable": "not_applicable",
    "unknown": "unknown",
}


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    clean = value.strip()
    return clean or None


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        match = re.search(r"\d+", value)
        return int(match.group()) if match else None
    return None


def _boolean(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        clean = value.strip().lower()
        if clean in {"yes", "true", "y", "1"}:
            return True
        if clean in {"no", "false", "n", "0"}:
            return False
    return None


def _choice(value: Any, aliases: dict[str, str]) -> str | None:
    clean = _text(value)
    if clean is None:
        return None
    return aliases.get(clean.lower())


def _date_value(value: Any) -> date | None:
    clean = _text(value)
    if clean is None:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(clean, fmt).date()
        except ValueError:
            continue
    return None


def _normalise(data: dict[str, Any], source: str) -> PVReportDraft:
    patient_data = data.get("patient") if isinstance(data.get("patient"), dict) else {}
    drug_data = data.get("drug") if isinstance(data.get("drug"), dict) else {}
    patient = PVPatientDraft(
        identifier=_text(patient_data.get("identifier")),
        age=_integer(patient_data.get("age")),
        age_group=_text(patient_data.get("age_group")),
        sex=_text(patient_data.get("sex")),
        initials=_text(patient_data.get("initials")),
        dob=_date_value(patient_data.get("dob")),
    )
    drug = PVDrugDraft(
        name=_text(drug_data.get("name")),
        batch_number=_text(drug_data.get("batch_number")),
        dose_text=_text(drug_data.get("dose_text")),
        route_of_administration=_text(drug_data.get("route_of_administration")),
        indication=_text(drug_data.get("indication")),
        action_taken=_choice(drug_data.get("action_taken"), _ACTION_ALIASES),
        therapy_start_date=_date_value(drug_data.get("therapy_start_date")),
        therapy_end_date=_date_value(drug_data.get("therapy_end_date")),
    )
    criteria = data.get("seriousness_criteria") or []
    if not isinstance(criteria, list):
        criteria = []
    return PVReportDraft(
        product_name=_text(data.get("product_name")),
        patient=patient,
        drug=drug,
        reaction_meddra_term=_text(data.get("reaction_meddra_term")),
        reaction_description=_text(data.get("reaction_description")),
        reaction_start_date=_date_value(data.get("reaction_start_date")),
        seriousness_criteria=[str(item).strip() for item in criteria if str(item).strip()],
        is_serious=_boolean(data.get("is_serious")),
        severity=_choice(data.get("severity"), _SEVERITY_ALIASES),
        causality=_choice(data.get("causality"), _CAUSALITY_ALIASES),
        outcome=_choice(data.get("outcome"), _OUTCOME_ALIASES),
        reporter_name=_text(data.get("reporter_name")),
        reporter_email=_text(data.get("reporter_email")),
        reporter_phone=_text(data.get("reporter_phone")),
        reporter_organisation=_text(data.get("reporter_organisation")),
        reporter_qualification=_text(data.get("reporter_qualification")),
        reporter_country=_text(data.get("reporter_country")),
        first_received_date=_date_value(data.get("first_received_date")),
        worldwide_unique_id=_text(data.get("worldwide_unique_id")),
        organization=_text(data.get("organization")),
        extraction_source=source,
    )


def _search(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip() or None


def _rule_based_extract(text: str, root: Path | None = None) -> PVReportDraft:
    product = _search(r"(?:product|suspect(?:ed)? drug|medication)\s*[:\-]\s*([^\n]+)", text)
    if product is None and root is not None:
        product = read_context(root).get("product_name") or None

    patient = PVPatientDraft(
        identifier=_search(r"(?:patient(?: name)?|initials)\s*[:\-]\s*([^\n]+)", text),
        age=_integer(_search(r"(?:age|aged)\s*[:\-]?\s*([^\n]+)", text)),
        sex=_search(r"(?:sex|gender)\s*[:\-]\s*([^\n]+)", text),
    )
    drug = PVDrugDraft(
        name=product,
        dose_text=_search(r"(?:dose|dose text)\s*[:\-]\s*([^\n]+)", text),
        route_of_administration=_search(r"route\s*[:\-]\s*([^\n]+)", text),
    )
    reaction = _search(r"(?:reaction|adverse event|event)\s*[:\-]\s*([^\n]+)", text)
    narrative = _search(r"(?:narrative|description|case description)\s*[:\-]\s*([^\n]+)", text)
    reporter = _search(r"reporter(?: name)?\s*[:\-]\s*([^\n]+)", text)
    seriousness = _search(r"(?:serious|seriousness)\s*[:\-]\s*([^\n]+)", text)

    return PVReportDraft(
        product_name=product,
        patient=patient,
        drug=drug,
        reaction_meddra_term=reaction,
        reaction_description=narrative,
        reaction_start_date=_date_value(_search(r"(?:reaction onset|onset date)\s*[:\-]\s*([^\n]+)", text)),
        is_serious=_boolean(seriousness),
        severity=_choice(_search(r"severity\s*[:\-]\s*([^\n]+)", text), _SEVERITY_ALIASES),
        causality=_choice(_search(r"causality\s*[:\-]\s*([^\n]+)", text), _CAUSALITY_ALIASES),
        outcome=_choice(_search(r"outcome\s*[:\-]\s*([^\n]+)", text), _OUTCOME_ALIASES),
        reporter_name=reporter,
        first_received_date=_date_value(_search(r"(?:first received|date received)\s*[:\-]\s*([^\n]+)", text)),
        extraction_source="rules",
    )


async def extract_report_fields(text: str, root: Path | None = None) -> PVReportDraft:
    """Extract a draft ADR report, falling back to deterministic label parsing."""
    if not text.strip():
        return PVReportDraft(extraction_source="rules")

    prompt = (
        "Extract a pharmacovigilance adverse drug reaction report from the source text. "
        "Return only JSON with optional keys: product_name, patient {identifier, age, sex, initials}, "
        "drug {name, dose_text, route_of_administration}, reaction_meddra_term, "
        "reaction_description, reaction_start_date, severity, causality, outcome, "
        "is_serious, reporter_name, reporter_email, reporter_phone, reporter_organisation, "
        "reporter_country, first_received_date. Use null for values not explicitly stated; never infer. "
        "Dates must use YYYY-MM-DD. Severity must be mild, moderate, severe, life_threatening, or fatal. "
        "Causality must be certain, probable, possible, unlikely, conditional, or unassessable. "
        "Outcome must be recovered, recovering, not_recovered, fatal, or unknown.\n\n"
        f"SOURCE:\n{text[:12000]}"
    )
    try:
        raw = await llm.generate_json(prompt)
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("extraction result is not an object")
        return _normalise(data, "llm")
    except Exception:
        return _rule_based_extract(text, root)
