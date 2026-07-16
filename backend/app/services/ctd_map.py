"""
dossiers/ctd_map.py
────────────────────────────────────────
Canonical ICH M4 (CTD) section map: {section_path: title} for all 5 modules.

This is the full standard structure used for classification grounding and for
the *generic* fill fallback. Sections that also have a bespoke schema in
section_schemas.py get higher-quality structured extraction; every other
section here can still be filled generically (title + CTD-purpose prompt).

Module 1 is region-specific; we keep the common administrative leaves used by
this platform. Modules 2–5 follow standard ICH M4 numbering.
"""

from __future__ import annotations

# Ordered for stable display. Leaf sections only (the ones documents map to).
CTD_MAP: dict[str, str] = {
    # ── Module 1 — Administrative (region-specific subset) ───────────────────
    "1.1": "Application Form / Cover Letter",
    "1.2": "Product Information",
    "1.3.1": "Summary of Product Characteristics (SmPC)",
    "1.3.2": "Labelling",
    "1.3.3": "Package Leaflet (PIL)",
    "1.4": "GMP Certificate",
    "1.5": "Patent and Exclusivity Information",
    "1.6": "Environmental Risk Assessment (ERA)",

    # ── Module 2 — Summaries ─────────────────────────────────────────────────
    "2.1": "CTD Table of Contents",
    "2.2": "CTD Introduction",
    "2.3": "Quality Overall Summary (QOS)",
    "2.4": "Nonclinical Overview",
    "2.5": "Clinical Overview",
    "2.6": "Nonclinical Written and Tabulated Summaries",
    "2.7": "Clinical Summary",

    # ── Module 3 — Quality: Drug Substance (3.2.S) ───────────────────────────
    "3.2.S.1.1": "Nomenclature (Drug Substance)",
    "3.2.S.1.2": "Structure (Drug Substance)",
    "3.2.S.1.3": "General Properties (Drug Substance)",
    "3.2.S.2.1": "Manufacturer (Drug Substance)",
    "3.2.S.2.2": "Description of Manufacturing Process and Process Controls (Drug Substance)",
    "3.2.S.2.3": "Control of Materials (Drug Substance)",
    "3.2.S.2.4": "Controls of Critical Steps and Intermediates (Drug Substance)",
    "3.2.S.2.5": "Process Validation and/or Evaluation (Drug Substance)",
    "3.2.S.2.6": "Manufacturing Process Development (Drug Substance)",
    "3.2.S.3.1": "Elucidation of Structure and other Characteristics",
    "3.2.S.3.2": "Impurities (Drug Substance)",
    "3.2.S.4.1": "Specification (Drug Substance)",
    "3.2.S.4.2": "Analytical Procedures (Drug Substance)",
    "3.2.S.4.3": "Validation of Analytical Procedures (Drug Substance)",
    "3.2.S.4.4": "Batch Analyses (Drug Substance)",
    "3.2.S.4.5": "Justification of Specification (Drug Substance)",
    "3.2.S.5": "Reference Standards or Materials (Drug Substance)",
    "3.2.S.6": "Container Closure System (Drug Substance)",
    "3.2.S.7.1": "Stability Summary and Conclusions (Drug Substance)",
    "3.2.S.7.2": "Post-approval Stability Protocol and Stability Commitment (Drug Substance)",
    "3.2.S.7.3": "Stability Data (Drug Substance)",

    # ── Module 3 — Quality: Drug Product (3.2.P) ─────────────────────────────
    "3.2.P.1": "Description and Composition (Drug Product)",
    "3.2.P.2.1": "Components of the Drug Product",
    "3.2.P.2.2": "Drug Product (Pharmaceutical Development)",
    "3.2.P.2.3": "Manufacturing Process Development",
    "3.2.P.2.4": "Container Closure System (Pharmaceutical Development)",
    "3.2.P.2.5": "Microbiological Attributes",
    "3.2.P.2.6": "Compatibility",
    "3.2.P.3.1": "Manufacturer (Drug Product)",
    "3.2.P.3.2": "Batch Formula",
    "3.2.P.3.3": "Description of Manufacturing Process and Process Controls",
    "3.2.P.3.4": "Controls of Critical Steps and Intermediates",
    "3.2.P.3.5": "Process Validation and/or Evaluation",
    "3.2.P.4.1": "Specifications (Excipients)",
    "3.2.P.4.2": "Analytical Procedures (Excipients)",
    "3.2.P.4.3": "Validation of Analytical Procedures (Excipients)",
    "3.2.P.4.4": "Justification of Specifications (Excipients)",
    "3.2.P.4.5": "Excipients of Human or Animal Origin",
    "3.2.P.4.6": "Novel Excipients",
    "3.2.P.5.1": "Specification (Drug Product)",
    "3.2.P.5.2": "Analytical Procedures (Drug Product)",
    "3.2.P.5.3": "Validation of Analytical Procedures (Drug Product)",
    "3.2.P.5.4": "Batch Analyses (Drug Product)",
    "3.2.P.5.5": "Characterisation of Impurities (Drug Product)",
    "3.2.P.5.6": "Justification of Specification(s) (Drug Product)",
    "3.2.P.6": "Reference Standards or Materials (Drug Product)",
    "3.2.P.7": "Container Closure System",
    "3.2.P.8.1": "Stability Summary and Conclusion (Drug Product)",
    "3.2.P.8.2": "Post-approval Stability Protocol and Stability Commitment (Drug Product)",
    "3.2.P.8.3": "Stability Data (Drug Product)",

    # ── Module 3 — Appendices & Regional ─────────────────────────────────────
    "3.2.A.1": "Facilities and Equipment",
    "3.2.A.2": "Adventitious Agents Safety Evaluation",
    "3.2.A.3": "Excipients (Appendices)",
    "3.2.R": "Regional Information",

    # ── Module 4 — Nonclinical Study Reports ─────────────────────────────────
    "4.2.1.1": "Primary Pharmacodynamics",
    "4.2.1.2": "Secondary Pharmacodynamics",
    "4.2.1.3": "Safety Pharmacology",
    "4.2.1.4": "Pharmacodynamic Drug Interactions",
    "4.2.2.1": "Analytical Methods and Validation Reports (Nonclinical PK)",
    "4.2.2.2": "Absorption",
    "4.2.2.3": "Distribution",
    "4.2.2.4": "Metabolism",
    "4.2.2.5": "Excretion",
    "4.2.2.6": "Pharmacokinetic Drug Interactions (Nonclinical)",
    "4.2.2.7": "Other Pharmacokinetic Studies",
    "4.2.3.1": "Single-Dose Toxicity",
    "4.2.3.2": "Repeat-Dose Toxicity",
    "4.2.3.3": "Genotoxicity",
    "4.2.3.4": "Carcinogenicity",
    "4.2.3.5": "Reproductive and Developmental Toxicity",
    "4.2.3.6": "Local Tolerance",
    "4.2.3.7": "Other Toxicity Studies",
    "4.3": "Literature References (Nonclinical)",

    # ── Module 5 — Clinical Study Reports ────────────────────────────────────
    "5.2": "Tabular Listing of All Clinical Studies",
    "5.3.1.1": "Reports of Bioavailability Studies",
    "5.3.1.2": "Comparative BA / Bioequivalence Study Reports",
    "5.3.1.3": "In Vitro–In Vivo Correlation Study Reports",
    "5.3.1.4": "Reports of Bioanalytical and Analytical Methods (Human Studies)",
    "5.3.2.1": "Plasma Protein Binding Study Reports",
    "5.3.2.2": "Reports of Hepatic Metabolism and Drug Interaction Studies",
    "5.3.2.3": "Reports of Studies Using Other Human Biomaterials",
    "5.3.3.1": "Healthy Subject PK and Initial Tolerability Study Reports",
    "5.3.3.2": "Patient PK and Initial Tolerability Study Reports",
    "5.3.3.3": "Intrinsic Factor PK Study Reports",
    "5.3.3.4": "Extrinsic Factor PK Study Reports",
    "5.3.3.5": "Population PK Study Reports",
    "5.3.4.1": "Healthy Subject PD and PK/PD Study Reports",
    "5.3.4.2": "Patient PD and PK/PD Study Reports",
    "5.3.5.1": "Reports of Controlled Clinical Studies",
    "5.3.5.2": "Reports of Uncontrolled Clinical Studies",
    "5.3.5.3": "Reports of Analyses of Data from More than One Study",
    "5.3.5.4": "Other Clinical Study Reports",
    "5.3.6": "Reports of Post-Marketing Experience",
    "5.3.7": "Case Report Forms and Individual Patient Listings",
    "5.4": "Literature References (Clinical)",
}


def get_ctd_title(section_path: str) -> str | None:
    """Return the standard ICH M4 title for a section path."""
    return CTD_MAP.get(section_path)


def is_valid_ctd_path(section_path: str) -> bool:
    return section_path in CTD_MAP


def all_ctd_paths() -> list[str]:
    return list(CTD_MAP.keys())
