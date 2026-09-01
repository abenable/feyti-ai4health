"""Minimum criteria utilities for ADR reports (pure functions).

All functions accept a plain ``dict`` representing an ADR report – typically the
``model_dump()`` of :class:`app.models.pv_schemas.ADRReport`. The implementation
mirrors the Django version from ``regulate-api-core`` but avoids any ORM
behaviour.
"""

from __future__ import annotations

from typing import Dict, List

# Ordering and human‑readable labels match the original implementation.
CRITERIA = ("patient", "reporter", "product", "reaction")
CRITERION_LABELS = {
    "patient": "an identifiable patient",
    "reporter": "an identifiable reporter",
    "product": "a suspect medicinal product",
    "reaction": "a suspect adverse reaction",
}

PATIENT_FIELDS = (
    "patient_identifier",
    "patient_age",
    "patient_age_group",
    "patient_sex",
    "patient_initials",
    "patient_dob",
)

REPORTER_FIELDS = (
    "reporter_name",
    "reporter_email",
    "reporter_phone",
    "reporter_organisation",
)

PRODUCT_FIELDS = ("product_name",)
REACTION_FIELDS = ("reaction_meddra_term", "reaction_description")

_CRITERION_FIELDS = {
    "patient": PATIENT_FIELDS,
    "reporter": REPORTER_FIELDS,
    "product": PRODUCT_FIELDS,
    "reaction": REACTION_FIELDS,
}


def _present(value) -> bool:
    """Return ``True`` if *value* counts as supplied.

    Mirrors the Django helper – ``0`` counts, empty strings/containers do not.
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    return True


def _get(source: Dict, field: str):
    return source.get(field)


def criteria_met(source: Dict) -> Dict[str, bool]:
    """Map each of the four criteria to a boolean indicating whether *source*
    satisfies it.
    """
    return {
        name: any(_present(_get(source, f)) for f in fields)
        for name, fields in _CRITERION_FIELDS.items()
    }


def missing_criteria(source: Dict) -> List[str]:
    """Return the list of criteria not satisfied, in conventional order.
    """
    met = criteria_met(source)
    return [name for name in CRITERIA if not met[name]]


def is_valid_icsr(source: Dict) -> bool:
    """True only when all four criteria are satisfied.
    """
    return not missing_criteria(source)


def describe_missing(source: Dict) -> str:
    """Human‑readable sentence describing what is still required, or ``""``.
    """
    missing = missing_criteria(source)
    if not missing:
        return ""
    labels = [CRITERION_LABELS[name] for name in missing]
    if len(labels) == 1:
        needed = labels[0]
    else:
        needed = ", ".join(labels[:-1]) + " and " + labels[-1]
    return f"Not yet a valid ICSR — still needs {needed}."


def reporter_contact(source: Dict) -> Dict[str, str]:
    """Return a dict with ``name``, ``email``, ``phone`` and ``organisation``.
    Empty strings are used instead of ``None`` for convenience.
    """
    return {
        "name": (_get(source, "reporter_name") or "").strip(),
        "email": (_get(source, "reporter_email") or "").strip(),
        "phone": (_get(source, "reporter_phone") or "").strip(),
        "organisation": (_get(source, "reporter_organisation") or "").strip(),
    }


def can_contact_reporter(source: Dict) -> bool:
    """True if either an email or a phone number is present.
    """
    contact = reporter_contact(source)
    return bool(contact["email"] or contact["phone"])
