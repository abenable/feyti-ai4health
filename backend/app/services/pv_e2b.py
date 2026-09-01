"""E2B(R3) ICSR generation for ADR reports.

This module is a lightweight port of the Django implementation. It works with
plain dictionaries (the ``model_dump()`` of :class:`app.models.pv_schemas.ADRReport`).
"""

from __future__ import annotations

import logging
from datetime import date
from xml.etree import ElementTree as ET
from typing import Dict, List, Optional

from app.services.pv_expectedness import assess

logger = logging.getLogger(__name__)

# ICH ICSR R2 / HL7 v3 namespace.
NS = "urn:hl7-org:v3"
XSI = "http://www.w3.org/2001/XMLSchema-instance"

INTERACTION_ID = "PORR_IN049016UV"

REPORT_TYPE_CODES = {
    "initial": "1",
    "followup": "1",
    "nullification": "1",
}

MESSAGE_TYPE_CODES = {
    "initial": "1",
    "followup": "2",
    "nullification": "3",
}

QUALIFICATION_CODES = {
    "physician": "1",
    "pharmacist": "2",
    "other_hcp": "3",
    "lawyer": "4",
    "consumer": "5",
}

SEX_CODES = {
    "male": "1", "m": "1",
    "female": "2", "f": "2",
}

OUTCOME_CODES = {
    "recovered": "1",
    "recovering": "2",
    "not_recovered": "3",
    "fatal": "5",
    "unknown": "6",
}

SERIOUSNESS_ELEMENTS = {
    "death": "seriousnessDeath",
    "life_threatening": "seriousnessLifeThreatening",
    "hospitalization": "seriousnessHospitalization",
    "hospitalisation": "seriousnessHospitalization",
    "disability": "seriousnessDisabling",
    "congenital": "seriousnessCongenitalAnomali",
    "other": "seriousnessOther",
}

ACTION_TAKEN_CODES = {
    "withdrawn": "1",
    "dose_reduced": "2",
    "dose_increased": "3",
    "dose_not_changed": "4",
    "unknown": "0",
    "not_applicable": "9",
}

_YES, _NO = "1", "2"


class E2BValidationError(Exception):
    """Raised when a report cannot be expressed as a conformant ICSR."""


def _fmt_datetime(value) -> str:
    return value.strftime("%Y%m%d%H%M%S")


def _fmt_date(value) -> str:
    if isinstance(value, str):
        value = date.fromisoformat(value)
    return value.strftime("%Y%m%d")


_PATIENT_FIELDS = ("identifier", "age", "age_group", "sex", "initials", "dob")
_DRUG_FIELDS = (
    "name", "batch_number", "dose_text", "route_of_administration", "indication",
    "action_taken", "therapy_start_date", "therapy_end_date",
)


def _normalise_report(report: Dict) -> Dict:
    """Flatten nested patient/drug objects for the ported E2B builder."""
    normalised = dict(report)
    patient = report.get("patient")
    if isinstance(patient, dict):
        for key in _PATIENT_FIELDS:
            normalised.setdefault(f"patient_{key}", patient.get(key))
    drug = report.get("drug")
    if isinstance(drug, dict):
        for key in _DRUG_FIELDS:
            normalised.setdefault(key, drug.get(key))
    return normalised


def validate(report: Dict) -> List[str]:
    report = _normalise_report(report)
    problems = []
    if not report.get("worldwide_unique_id"):
        problems.append(
            "The case has no worldwide unique identifier (C.1.8.1), so a regulator could not match a later follow-up to it."
        )
    if not report.get("product_name"):
        problems.append("No suspect product is named (G.k.2.2).")
    if not (report.get("reaction_meddra_term") or report.get("reaction_description")):
        problems.append("No reaction is described (E.i.1.1a).")
    if not report.get("reaction_pt_code"):
        problems.append(
            "The reaction is not coded to MedDRA (E.i.2.1b). A regulator cannot receive a free-text reaction term."
        )
    if not report.get("first_received_date"):
        problems.append(
            "No date is recorded for when the organisation first became aware of the case (C.1.4)."
        )
    # Minimum criteria check – reuse the pure‑function implementation.
    from app.services import pv_minimum_criteria

    for criterion in pv_minimum_criteria.missing_criteria(report):
        if criterion == "reporter":
            problems.append(
                "No identifiable reporter (C.2.r) — one of the four minimum criteria for a valid ICSR."
            )
        elif criterion == "patient":
            problems.append(
                "No identifiable patient (D) — one of the four minimum criteria for a valid ICSR."
            )
    if report.get("case_report_type") == "nullification" and not report.get("nullification_reason"):
        problems.append("A nullification must state its reason (C.1.11.2).")
    return problems


def _sub(parent, tag, **attrs):
    return ET.SubElement(parent, f"{{{NS}}}{tag}", attrs)


def _value(parent, tag, code=None, text=None, null="NI"):
    element = _sub(parent, tag)
    if code:
        element.set("code", str(code))
    elif text is not None and str(text).strip():
        element.text = str(text)
    else:
        element.set("nullFlavor", null)
    return element


def build_icsr(report: Dict, *, sender_id: str, receiver_id: str) -> str:
    report = _normalise_report(report)
    problems = validate(report)
    if problems:
        raise E2BValidationError("This case cannot be sent as E2B(R3):\n  - " + "\n  - ".join(problems))

    ET.register_namespace('', NS)
    ET.register_namespace('xsi', XSI)

    root = ET.Element(f"{{{NS}}}{INTERACTION_ID}")
    root.set(f"{{{XSI}}}schemaLocation", f"{NS} multicacheschemas/{INTERACTION_ID}.xsd")

    _sub(root, 'id', extension=report.get('worldwide_unique_id'), root='2.16.840.1.113883.3.989.2.1.3.1')
    _sub(root, 'creationTime', value=_fmt_datetime(date.today()))
    _sub(root, 'interactionId', extension=INTERACTION_ID, root='2.16.840.1.113883.1.6')
    _sub(root, 'processingCode', code='P')
    _sub(root, 'processingModeCode', code='T')
    _sub(root, 'acceptAckCode', code='AL')

    receiver = _sub(root, 'receiver', typeCode='RCV')
    device = _sub(receiver, 'device')
    _sub(device, 'id', extension=receiver_id, root='2.16.840.1.113883.3.989.2.1.3.14')

    sender = _sub(root, 'sender', typeCode='SND')
    sender_device = _sub(sender, 'device')
    _sub(sender_device, 'id', extension=sender_id, root='2.16.840.1.113883.3.989.2.1.3.13')

    control = _sub(root, 'controlActProcess', classCode='CACT', moodCode='EVN')
    _sub(control, 'code', code=INTERACTION_ID, codeSystem='2.16.840.1.113883.1.6')
    subject = _sub(control, 'subject', typeCode='SUBJ')
    investigation = _sub(subject, 'investigationEvent', classCode='INVSTG', moodCode='EVN')

    _sub(investigation, 'id', extension=report.get('worldwide_unique_id'), root='2.16.840.1.113883.3.989.2.1.3.1')
    _sub(investigation, 'code', code='PAT_RPT', codeSystem='2.16.840.1.113883.5.4')

    text_el = _sub(investigation, 'text')
    text_el.text = f"Version {report.get('case_version', 1)}"

    effective = _sub(investigation, 'effectiveTime')
    _sub(effective, 'low', value=_fmt_date(report.get('first_received_date')))

    _sub(investigation, 'statusCode', code=MESSAGE_TYPE_CODES.get(report.get('case_report_type'), '1'))

    if report.get('case_report_type') == 'nullification':
        reason = _sub(investigation, 'subjectOf1', typeCode='SUBJ')
        control_act = _sub(reason, 'controlActEvent', classCode='CACT', moodCode='EVN')
        _sub(control_act, 'code', code='1', codeSystem='2.16.840.1.113883.3.989.2.1.1.14')
        reason_text = _sub(control_act, 'text')
        reason_text.text = report.get('nullification_reason')

    _build_reporter(investigation, report)
    _build_patient(investigation, report)

    return ET.tostring(root, encoding='unicode', xml_declaration=True)


def _build_reporter(investigation, report):
    component = _sub(investigation, 'subjectOf2', typeCode='SUBJ')
    role = _sub(component, 'primaryRole', classCode='PRS')
    name_el = _sub(role, 'name')
    if report.get('reporter_name'):
        name_el.text = report['reporter_name']
    else:
        name_el.set('nullFlavor', 'NI')
    _value(role, 'code', code=QUALIFICATION_CODES.get(report.get('reporter_qualification')))
    address = _sub(role, 'addr')
    country_el = _sub(address, 'country')
    if report.get('reporter_country') or report.get('country'):
        country_el.text = report.get('reporter_country') or report.get('country')
    else:
        country_el.set('nullFlavor', 'NI')
    if report.get('reporter_organisation'):
        org = _sub(role, 'representedOrganization', classCode='ORG')
        org_name = _sub(org, 'name')
        org_name.text = report['reporter_organisation']


def _build_patient(investigation, report):
    component = _sub(investigation, 'subject2', typeCode='SUBJ')
    patient = _sub(component, 'primaryRole', classCode='INVSBJ')
    _value(patient, 'id', text=report.get('patient_identifier'))
    person = _sub(patient, 'player1', classCode='PSN', determinerCode='INSTANCE')
    _value(person, 'administrativeGenderCode', code=SEX_CODES.get((report.get('patient_sex') or '').strip().lower()))
    if report.get('patient_age') is not None:
        age_observation = _sub(person, 'subjectOf2', typeCode='SBJ')
        observation = _sub(age_observation, 'observation', classCode='OBS', moodCode='EVN')
        _sub(observation, 'code', code='3', codeSystem='2.16.840.1.113883.3.989.2.1.1.26')
        _sub(observation, 'value', value=str(report['patient_age']), unit='a')
    _build_reaction(patient, report)
    _build_drug(patient, report)


def _build_reaction(patient, report):
    component = _sub(patient, 'subjectOf2', typeCode='SBJ')
    observation = _sub(component, 'observation', classCode='OBS', moodCode='EVN')
    _sub(observation, 'code', code='29', codeSystem='2.16.840.1.113883.3.989.2.1.1.19')
    verbatim = _sub(observation, 'text')
    verbatim.text = report.get('reaction_meddra_term') or report.get('reaction_description')
    if report.get('reaction_start_date'):
        effective = _sub(observation, 'effectiveTime')
        _sub(effective, 'low', value=_fmt_date(report['reaction_start_date']))
    _sub(observation, 'value', code=str(report.get('reaction_pt_code')), codeSystem='2.16.840.1.113883.6.163', codeSystemVersion=report.get('meddra_version') or '', displayName=report.get('reaction_pt_name'))
    for criterion in (report.get('seriousness_criteria') or []):
        element = SERIOUSNESS_ELEMENTS.get(str(criterion).strip().lower())
        if element:
            serious = _sub(observation, 'outboundRelationship2', typeCode='PERT')
            serious_obs = _sub(serious, 'observation', classCode='OBS', moodCode='EVN')
            _sub(serious_obs, 'code', code=element, codeSystem='2.16.840.1.113883.3.989.2.1.1.19')
            _sub(serious_obs, 'value', value='true')
    outcome = _sub(observation, 'outboundRelationship2', typeCode='PERT')
    outcome_obs = _sub(outcome, 'observation', classCode='OBS', moodCode='EVN')
    _sub(outcome_obs, 'code', code='27', codeSystem='2.16.840.1.113883.3.989.2.1.1.19')
    _value(outcome_obs, 'value', code=OUTCOME_CODES.get(report.get('outcome')), null='UNK')


def _build_drug(patient, report):
    component = _sub(patient, 'subjectOf2', typeCode='SBJ')
    administration = _sub(component, 'substanceAdministration', classCode='SBADM', moodCode='EVN')
    _sub(administration, 'code', code='1', codeSystem='2.16.840.1.113883.3.989.2.1.1.13')
    if report.get('therapy_start_date') or report.get('therapy_end_date'):
        effective = _sub(administration, 'effectiveTime')
        if report.get('therapy_start_date'):
            _sub(effective, 'low', value=_fmt_date(report['therapy_start_date']))
        if report.get('therapy_end_date'):
            _sub(effective, 'high', value=_fmt_date(report['therapy_end_date']))
    if report.get('route_of_administration'):
        route = _sub(administration, 'routeCode')
        route.set('nullFlavor', 'NI')
        route_text = _sub(route, 'originalText')
        route_text.text = report['route_of_administration']
    if report.get('dose_text'):
        dose = _sub(administration, 'doseQuantity')
        dose.set('nullFlavor', 'NI')
        dose_text = _sub(dose, 'originalText')
        dose_text.text = report['dose_text']
    consumable = _sub(administration, 'consumable', classCode='CSM')
    product_role = _sub(consumable, 'instanceOfKind', classCode='INST')
    kind = _sub(product_role, 'kindOfProduct', classCode='MMAT', determinerCode='KIND')
    name = _sub(kind, 'name')
    name.text = report.get('product_name')
    if report.get('batch_number'):
        lot = _sub(product_role, 'lotNumberText')
        lot.text = report['batch_number']
    if report.get('indication'):
        indication = _sub(administration, 'inboundRelationship', typeCode='RSON')
        observation = _sub(indication, 'observation', classCode='OBS', moodCode='EVN')
        _sub(observation, 'code', code='19', codeSystem='2.16.840.1.113883.3.989.2.1.1.19')
        value = _sub(observation, 'value')
        value.set('nullFlavor', 'NI')
        original = _sub(value, 'originalText')
        original.text = report['indication']
    if report.get('action_taken'):
        action = _sub(administration, 'outboundRelationship2', typeCode='PERT')
        observation = _sub(action, 'observation', classCode='OBS', moodCode='EVN')
        _sub(observation, 'code', code='31', codeSystem='2.16.840.1.113883.3.989.2.1.1.19')
        _sub(observation, 'value', code=ACTION_TAKEN_CODES.get(report.get('action_taken'), '0'), codeSystem='2.16.840.1.113883.3.989.2.1.1.15')
    # Challenge handling omitted for brevity.
