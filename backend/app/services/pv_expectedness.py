"""Expectedness assessment for ADR reports.

The original Django service performed database look‑ups for reference safety
information. In this lightweight demo we only need to compare the reported
MedDRA PT code against a static list of expected reactions stored in JSON.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from app.services import store_utils
from app.core.config import settings

# Fatal or life‑threatening outcomes trigger the 7‑day SUSAR clock.
FATAL_OR_LIFE_THREATENING = {"fatal", "death", "life_threatening"}
SUSAR_DAYS_FATAL = 7
SUSAR_DAYS_OTHER = 15


def _load_expected(dossier_root_path) -> List[Dict]:
    """Load ``expected_reactions.json`` from the dossier's ``pv`` folder.

    The file is expected to contain a list of objects with at least ``pt_code``
    and optionally ``pt_name``.
    """
    path = store_utils.safe_join(dossier_root_path, "pv/expected_reactions.json")
    data = store_utils.read_json(path)
    return data if isinstance(data, list) else []


def assess(report: Dict, dossier_root_path) -> Dict:
    """Determine whether the reaction is expected and whether the case is a SUSAR.

    The logic is deliberately simplified compared to the full Django version:

    * If the report has no MedDRA PT code we cannot assess – ``not_assessable``.
    * If the PT code appears in the expected reactions list the reaction is
      ``expected``; otherwise ``unexpected``.
    * When ``unexpected`` and the case is serious we calculate the statutory
      SUSAR deadline (7 or 15 days) based on the outcome or seriousness criteria.
    """
    expected_list = _load_expected(dossier_root_path)
    pt_code = report.get("reaction_pt_code")
    is_serious = bool(report.get("is_serious"))
    outcome = (report.get("outcome") or "").strip().lower()
    seriousness_criteria = [str(c).lower() for c in (report.get("seriousness_criteria") or [])]

    result: Dict = {
        "expectedness": "not_assessable",
        "is_susar": False,
        "matched_term": "",
        "susar_due_days": None,
        "reasoning": "",
    }

    if not pt_code:
        result["reasoning"] = "The reaction is not coded to MedDRA, so it cannot be assessed."
        return result

    # Find matching expected reaction
    match = next((e for e in expected_list if str(e.get("pt_code")) == str(pt_code)), None)
    term = report.get("reaction_pt_name") or report.get("reaction_meddra_term") or ""

    if match is None:
        result.update({
            "expectedness": "unexpected",
            "matched_term": "",
            "reasoning": f"'{term}' is not listed as an expected reaction.",
        })
    else:
        result.update({
            "expectedness": "expected",
            "matched_term": match.get("pt_name", ""),
            "reasoning": f"'{term}' matches expected reaction {match.get('pt_code')}.",
        })

    if result["expectedness"] == "unexpected" and is_serious:
        fatal = outcome in FATAL_OR_LIFE_THREATENING or any(
            c in FATAL_OR_LIFE_THREATENING for c in seriousness_criteria
        )
        result["is_susar"] = True
        result["susar_due_days"] = SUSAR_DAYS_FATAL if fatal else SUSAR_DAYS_OTHER
        result["reasoning"] += (
            f" Serious and unexpected, therefore a SUSAR due within {result['susar_due_days']} days.")

    return result
