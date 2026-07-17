"""
dossiers/ctd_map.py
────────────────────────────────────────
Canonical ICH M4 (CTD) section map: {section_path: title} for all 5 modules.

Derived from the authoritative, ICH-M4-corrected structure in
`ctd_structure.py` (vendored from regulate-api-core) via its get_flat_index().
That file is the single source of truth — edit the structure there, not here.

Module 1 is region-specific; we default to Uganda (NDA). Change DEFAULT_REGION
to build the map for another authority (kenya, tanzania, who, eu, nigeria, …).

Used for classification grounding: every leaf/parent CTD node is a valid target
so an uploaded document can be placed at its most specific node when building
the dossier.
"""

from __future__ import annotations

import re

from app.services.ctd_structure import get_flat_index

DEFAULT_REGION = "uganda"

# Full ICH catalogue (parents + leaves). Drop the "[name, dosage form]" /
# "[Uganda NDA Form 1]" template placeholders so user-facing titles read clean.
# ponytail: full flat index — if the fine-grained tabulated-summary leaves
# (e.g. 2.6.6.10) start hurting classification, curate a document-level subset
# right here; nothing else needs to change.
CTD_MAP: dict[str, str] = {
    path: re.sub(r"\s*\[.*?\]", "", title).strip()
    for path, title in get_flat_index(DEFAULT_REGION).items()
}


def get_ctd_title(section_path: str) -> str | None:
    """Return the standard ICH M4 title for a section path."""
    return CTD_MAP.get(section_path)


def is_valid_ctd_path(section_path: str) -> bool:
    return section_path in CTD_MAP


def all_ctd_paths() -> list[str]:
    return list(CTD_MAP.keys())


if __name__ == "__main__":  # ponytail self-check: python -m app.services.ctd_map
    assert CTD_MAP["3.2.P.8.3"].startswith("Stability Data"), CTD_MAP.get("3.2.P.8.3")
    assert CTD_MAP["5.3.5.4"] == "Other Study Reports", CTD_MAP.get("5.3.5.4")
    assert "1.2" in CTD_MAP, "classification fallback section 1.2 must exist"
    assert all(p.split(".")[0] in {"1", "2", "3", "4", "5"} for p in CTD_MAP)
    print(f"OK — {len(CTD_MAP)} CTD sections (region={DEFAULT_REGION})")
