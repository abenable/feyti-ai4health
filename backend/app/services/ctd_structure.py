# dossier/ctd_structure.py
#
# CTD / eCTD Module Structure — ICH M4 Compliant
#
# Sources (official ICH guidance documents):
#   ICH M4Q (R1) — Quality:      https://www.fda.gov/media/71581/download
#   ICH M4S       — Safety:      https://www.fda.gov/media/71628/download
#   ICH M4E       — Efficacy:    https://www.fda.gov/media/71610/download
#   ICH M4 (R4)   — Organisation: https://www.ich.org/page/ctd
#
# STRUCTURE NOTES:
#   Module 1   : Region-specific — NOT part of the harmonized CTD
#   Modules 2-5: Globally harmonized (ICH standard)
#
# CORRECTIONS FROM PREVIOUS VERSION:
#   [2.3]   QOS DOES have S/P/A/R sub-sections per ICH M4Q. They are
#           internal headings within one document, not separate eCTD files.
#   [2.4]   Nonclinical Overview has 2.4.1-2.4.6 per ICH M4S.
#   [2.5]   Clinical Overview has 2.5.1-2.5.7 per ICH M4E.
#   [2.6]   Sub-section numbering corrected: 2.6.2 = Pharmacology Written
#           Summary (not 2.6.1). 2.6.1 = Introduction. Full internal
#           structure of 2.6.2, 2.6.4, 2.6.6 added per M4S.
#   [2.7]   Full internal structure of 2.7.1-2.7.4 added per M4E.
#   [3.2.P.4] Added missing 3.2.P.4.5 and 3.2.P.4.6 per ICH M4Q.
#   [5.3.5.4] Corrected title to "Other Study Reports" per M4E.


# ---------------------------------------------------------------------------
# MODULE 1 - Regional Administrative Information
# NOT part of the harmonized CTD - varies by regulatory authority
# ---------------------------------------------------------------------------

CTD_MODULE_1 = {
    "uganda": {
        "title": "Module 1: Administrative Information (Uganda - NDA)",
        "region": "Uganda",
        "authority": "National Drug Authority (NDA)",
        "harmonized": False,
        "children": {
            "1.1": {"title": "Application Forms [Uganda NDA Form 1]"},
            "1.2": {"title": "Cover Letters"},
            "1.3": {
                "title": "Administrative Information",
                "children": {
                    "1.3.1": {"title": "Applicant Information"},
                    "1.3.2": {"title": "Field Copy Certification"},
                    "1.3.3": {"title": "Debarment Certification"},
                    "1.3.4": {"title": "Financial Certification and Disclosure"},
                    "1.3.5": {
                        "title": "Patent and Exclusivity",
                        "children": {
                            "1.3.5.1": {"title": "Patent Information"},
                            "1.3.5.2": {"title": "Patent Certification"},
                            "1.3.5.3": {"title": "Exclusivity Claim"},
                        },
                    },
                    "1.3.6": {"title": "Tropical Disease Priority Review Voucher"},
                },
            },
            "1.4": {
                "title": "References",
                "children": {
                    "1.4.1": {"title": "Letter of Authorization"},
                    "1.4.2": {"title": "Statement of Right of Reference"},
                    "1.4.3": {"title": "List of Authorized Persons to Incorporate by Reference"},
                    "1.4.4": {"title": "Cross-reference to Previously Submitted Information"},
                },
            },
            "1.5": {
                "title": "Application Status",
                "children": {
                    "1.5.1": {"title": "Withdrawal of an IND"},
                    "1.5.2": {"title": "Inactivation Request"},
                    "1.5.3": {"title": "Reactivation Request"},
                    "1.5.4": {"title": "Reinstatement Request"},
                    "1.5.5": {"title": "Withdrawal of an Unapproved Application or Supplement"},
                    "1.5.6": {"title": "Withdrawal of Listed Drug"},
                    "1.5.7": {"title": "Withdrawal of Approval of an Application or Revocation of License"},
                },
            },
            "1.6": {
                "title": "Meetings",
                "children": {
                    "1.6.1": {"title": "Meeting Request"},
                    "1.6.2": {"title": "Meeting Background Materials"},
                    "1.6.3": {"title": "Correspondence Regarding Meetings"},
                },
            },
            "1.7": {
                "title": "Fast Track / Priority Review",
                "children": {
                    "1.7.1": {"title": "Fast Track Designation Request"},
                    "1.7.2": {"title": "Fast Track Designation Withdrawal Request"},
                    "1.7.3": {"title": "Rolling Review Request"},
                    "1.7.4": {"title": "Correspondence Regarding Fast Track / Rolling Review"},
                },
            },
            "1.8": {
                "title": "Special Protocol Assessment Request",
                "children": {
                    "1.8.1": {"title": "Clinical Study"},
                    "1.8.2": {"title": "Carcinogenicity Study"},
                    "1.8.3": {"title": "Stability Study"},
                    "1.8.4": {"title": "Animal Efficacy Study for Approval Under the Animal Rule"},
                },
            },
            "1.9": {
                "title": "Pediatric Administrative Information",
                "children": {
                    "1.9.1": {"title": "Request for Waiver of Pediatric Studies"},
                    "1.9.2": {"title": "Request for Deferral of Pediatric Studies"},
                    "1.9.3": {"title": "Request for Pediatric Exclusivity Determination"},
                    "1.9.4": {"title": "Proposed Pediatric Study Request and Amendments"},
                    "1.9.5": {"title": "Other Correspondence Regarding Pediatric Exclusivity or Study Plans"},
                },
            },
            "1.10": {
                "title": "Dispute Resolution",
                "children": {
                    "1.10.1": {"title": "Request for Dispute Resolution"},
                    "1.10.2": {"title": "Correspondence Related to Dispute Resolution"},
                },
            },
            "1.11": {
                "title": "Information Amendment: Not Covered Under Modules 2-5",
                "children": {
                    "1.11.1": {"title": "Quality Information Amendment"},
                    "1.11.2": {"title": "Nonclinical Information Amendment"},
                    "1.11.3": {"title": "Clinical Information Amendment"},
                    "1.11.4": {"title": "Multiple Module Information Amendment"},
                },
            },
            "1.12": {
                "title": "Other Correspondence",
                "children": {
                    "1.12.1": {"title": "Pre-IND / Pre-Submission Correspondence"},
                    "1.12.2": {"title": "Request to Charge for Clinical Trial"},
                    "1.12.3": {"title": "Request to Charge for Investigational Drug"},
                    "1.12.4": {"title": "Miscellaneous Correspondence"},
                },
            },
            "1.13": {"title": "Annual Reports"},
            "1.14": {"title": "Adverse Event Reporting (AER / Pharmacovigilance Reports)"},
            "1.15": {"title": "Promotional Labeling and Advertising"},
            "1.16": {"title": "User Fee Cover Sheet (Uganda NDA)"},
        },
    },

    "kenya": {
        "title": "Module 1: Administrative Information (Kenya - PPB)",
        "region": "Kenya",
        "authority": "Pharmacy and Poisons Board (PPB)",
        "harmonized": False,
        "children": {
            "1.1": {"title": "Application Forms [Kenya PPB Form 1]"},
            "1.2": {"title": "Cover Letters"},
            "1.3": {
                "title": "Administrative Information",
                "children": {
                    "1.3.1": {"title": "Applicant Information"},
                    "1.3.2": {"title": "Field Copy Certification"},
                    "1.3.3": {"title": "Debarment Certification"},
                    "1.3.4": {"title": "Financial Certification and Disclosure"},
                },
            },
            "1.4": {
                "title": "References",
                "children": {
                    "1.4.1": {"title": "Letter of Authorization"},
                    "1.4.2": {"title": "Statement of Right of Reference"},
                },
            },
            "1.5":  {"title": "Application Status"},
            "1.6":  {"title": "Meetings"},
            "1.7":  {"title": "Fast Track / Priority Review"},
            "1.8":  {"title": "Special Protocol Assessment Request"},
            "1.9":  {"title": "Pediatric Administrative Information"},
            "1.10": {"title": "Dispute Resolution"},
            "1.11": {"title": "Information Amendment: Not Covered Under Modules 2-5"},
            "1.12": {"title": "Other Correspondence"},
            "1.13": {"title": "Annual Reports"},
            "1.14": {"title": "Adverse Event Reporting (AER / Pharmacovigilance Reports)"},
            "1.15": {"title": "Promotional Labeling and Advertising"},
            "1.16": {"title": "User Fee Cover Sheet (Kenya PPB)"},
        },
    },

    "tanzania": {
        "title": "Module 1: Administrative Information (Tanzania - TMDA)",
        "region": "Tanzania",
        "authority": "Tanzania Medicines and Medical Devices Authority (TMDA)",
        "harmonized": False,
        "children": {
            "1.1": {"title": "Application Forms [Tanzania TMDA Form 1]"},
            "1.2": {"title": "Cover Letters"},
            "1.3": {
                "title": "Administrative Information",
                "children": {
                    "1.3.1": {"title": "Applicant Information"},
                },
            },
            "1.4":  {"title": "References"},
            "1.5":  {"title": "Application Status"},
            "1.6":  {"title": "Meetings"},
            "1.7":  {"title": "Fast Track / Priority Review"},
            "1.8":  {"title": "Special Protocol Assessment Request"},
            "1.9":  {"title": "Pediatric Administrative Information"},
            "1.10": {"title": "Dispute Resolution"},
            "1.11": {"title": "Information Amendment: Not Covered Under Modules 2-5"},
            "1.12": {"title": "Other Correspondence"},
            "1.13": {"title": "Annual Reports"},
            "1.14": {"title": "Adverse Event Reporting (AER / Pharmacovigilance Reports)"},
            "1.15": {"title": "Promotional Labeling and Advertising"},
            "1.16": {"title": "User Fee Cover Sheet (Tanzania TMDA)"},
        },
    },

    # ── WHO-harmonized Module 1 (WHO TRS 1033, Annex 1) ────────────────────
    # Used as the default for countries without a specific template.
    # Section numbers follow WHO CTD guidance for NRAs (2022 edition).
    "who": {
        "title": "Module 1: Administrative Information (WHO Harmonized)",
        "region": "WHO",
        "authority": "National Regulatory Authority",
        "harmonized": True,
        "children": {
            "1.0": {"title": "Comprehensive Table of Contents"},
            "1.1": {"title": "Application Form"},
            "1.2": {"title": "Cover Letter"},
            "1.3": {
                "title": "Labelling",
                "children": {
                    "1.3.1": {"title": "Summary of Product Characteristics (SmPC)"},
                    "1.3.2": {"title": "Mock-up Labels and Artwork"},
                    "1.3.3": {"title": "Package Insert / Patient Information Leaflet"},
                },
            },
            "1.4": {
                "title": "Information about the Experts",
                "children": {
                    "1.4.1": {"title": "Quality Expert Report"},
                    "1.4.2": {"title": "Nonclinical Expert Overview"},
                    "1.4.3": {"title": "Clinical Expert Overview"},
                },
            },
            "1.5": {
                "title": "Specific Requirements for Different Types of Applications",
                "children": {
                    "1.5.1": {"title": "Information for Bibliographic Applications"},
                    "1.5.2": {"title": "Information for Generic Applications (Bioequivalence)"},
                    "1.5.3": {"title": "Information for Well-Established Use Applications"},
                    "1.5.4": {"title": "Information for Fixed-Dose Combinations"},
                },
            },
            "1.6": {"title": "Environmental Risk Assessment"},
            "1.7": {"title": "Information Relating to Orphan Drug Status"},
            "1.8": {
                "title": "Documents Relating to GMP and Licensing",
                "children": {
                    "1.8.1": {"title": "GMP Certificate of Manufacturer"},
                    "1.8.2": {"title": "Certificate of Pharmaceutical Product (CPP)"},
                    "1.8.3": {"title": "Free Sale Certificate"},
                    "1.8.4": {"title": "Manufacturing Authorization"},
                },
            },
            "1.9": {
                "title": "Pediatric Studies Information",
                "children": {
                    "1.9.1": {"title": "Pediatric Investigation Plan or Waiver"},
                    "1.9.2": {"title": "Pediatric Study Reports"},
                },
            },
            "1.10": {
                "title": "Information Relating to Pharmacovigilance",
                "children": {
                    "1.10.1": {"title": "Risk Management Plan (RMP)"},
                    "1.10.2": {"title": "Pharmacovigilance System Summary"},
                    "1.10.3": {"title": "Post-Approval Safety Studies"},
                },
            },
            "1.11": {
                "title": "Clinical Trials",
                "children": {
                    "1.11.1": {"title": "Clinical Trial Authorization(s)"},
                    "1.11.2": {"title": "Ethics Committee Approvals"},
                },
            },
            "1.12": {"title": "Samples"},
            "1.13": {"title": "Administrative / Financial Information"},
            "1.14": {"title": "Other Correspondence and Commitments"},
        },
    },

    # ── EU (EMA) Module 1 ───────────────────────────────────────────────────
    # Source: EMA/CHMP/ICH/4518/2001 + eSubmission Road Map v1.5 (2024)
    # Sections follow the EU CTD Module 1 structure for centralised,
    # mutual-recognition, and decentralised procedures.
    # Reference: https://www.ema.europa.eu/en/human-regulatory-overview/
    #            marketing-authorisation/applying-marketing-authorisation/
    #            module-1-administrative-information
    "eu": {
        "title": "Module 1: Administrative Information (EU — EMA)",
        "region": "European Union",
        "authority": "European Medicines Agency (EMA) / National Competent Authorities",
        "harmonized": False,
        "procedure": ["centralised", "mutual_recognition", "decentralised", "national"],
        "children": {
            "1.0": {"title": "Covering Letter"},
            "1.1": {
                "title": "Comprehensive Table of Contents",
                "children": {
                    "1.1.1": {"title": "Comprehensive Table of Contents (Module 1)"},
                    "1.1.2": {"title": "Comprehensive Table of Contents (Modules 2–5)"},
                },
            },
            "1.2": {
                "title": "Application Form",
                "children": {
                    "1.2.1": {"title": "Application Form (eAF — Human)"},
                    "1.2.2": {"title": "Declared Active Substances"},
                },
            },
            "1.3": {
                "title": "Product Information",
                "children": {
                    "1.3.1": {"title": "Summary of Product Characteristics (SmPC)"},
                    "1.3.2": {"title": "Labelling — Outer / Immediate Packaging"},
                    "1.3.3": {"title": "Package Leaflet (Patient Information Leaflet)"},
                    "1.3.4": {"title": "Mock-up Specimens (Artwork)"},
                    "1.3.5": {"title": "Specimens (Actual Samples if Required)"},
                    "1.3.6": {"title": "Braille Assessment"},
                    "1.3.7": {"title": "Product Information already approved in the EU (Reference Product)"},
                },
            },
            "1.4": {
                "title": "Information about the Experts",
                "children": {
                    "1.4.1": {"title": "Quality — Qualified Person / Expert CV and Declaration"},
                    "1.4.2": {"title": "Nonclinical — Expert CV and Declaration"},
                    "1.4.3": {"title": "Clinical — Expert CV and Declaration"},
                },
            },
            "1.5": {
                "title": "Specific Requirements for Different Types of Applications",
                "children": {
                    "1.5.1": {"title": "Known-Active-Substance Application (Art. 10a — Well-established use)"},
                    "1.5.2": {"title": "Generic Application (Art. 10(1)) — Bioequivalence Study Report"},
                    "1.5.3": {"title": "Hybrid Application (Art. 10(3))"},
                    "1.5.4": {"title": "Biosimilar Application (Art. 10(4)) — Comparability Data"},
                    "1.5.5": {"title": "Fixed-Dose Combination — Individual Component Justification"},
                    "1.5.6": {"title": "Informed Consent (Art. 10c — duplication of originator file)"},
                    "1.5.7": {"title": "Exceptional Circumstances Justification (Art. 14(8))"},
                    "1.5.8": {"title": "Conditional Marketing Authorisation Justification (Reg. 507/2006)"},
                },
            },
            "1.6": {
                "title": "Environmental Risk Assessment (ERA)",
                "children": {
                    "1.6.1": {"title": "Non-GMO ERA (Directive 2001/83/EC Annex I Part IV)"},
                    "1.6.2": {"title": "GMO ERA (Directive 2001/18/EC)"},
                },
            },
            "1.7": {
                "title": "Information Relating to Orphan Market Exclusivity",
                "children": {
                    "1.7.1": {"title": "Similar Medicinal Products"},
                    "1.7.2": {"title": "Orphan Designation Letter / COMP Opinion"},
                },
            },
            "1.8": {
                "title": "Information Relating to Pharmacovigilance",
                "children": {
                    "1.8.1": {"title": "Pharmacovigilance System Master File (PSMF) Summary"},
                    "1.8.2": {"title": "Risk Management Plan (RMP) — EU Module VI"},
                    "1.8.3": {"title": "Summary Bridging Report / Addendum to Clinical Overview"},
                },
            },
            "1.9": {
                "title": "Information Relating to Clinical Trials",
                "children": {
                    "1.9.1": {"title": "Paediatric Investigation Plan (PIP) / PIP Waiver Decision (PDCO)"},
                    "1.9.2": {"title": "Results of all Studies Conducted in Accordance with Agreed PIP"},
                },
            },
            "1.10": {
                "title": "Information Relating to Pharmacoeconomics",
                "note": "Optional — submitted to relevant national competent authority if required.",
            },
            "1.11": {
                "title": "Proof of Payment of Fees",
                "children": {
                    "1.11.1": {"title": "EMA Fee Payment Proof (Centralised Procedure)"},
                    "1.11.2": {"title": "National Authority Fee Payment Proof (MR/DC/National)"},
                },
            },
            "1.12": {
                "title": "Summary of Product Characteristics, Labelling and Package Leaflet — Agreed in Referral",
                "note": "Only for referral / repeat-use procedures.",
            },
            "1.13": {
                "title": "Documents Submitted in other Languages",
                "note": "Translations of SmPC/PIL/labelling per member state language requirement.",
            },
            "1.14": {
                "title": "List of Countries where the Application is / has been Submitted",
            },
            "1.15": {
                "title": "GMP-related Documents",
                "children": {
                    "1.15.1": {"title": "GMP Certificate(s) / EMA GMP Compliance Statement"},
                    "1.15.2": {"title": "Manufacturing Authorisation(s)"},
                    "1.15.3": {"title": "Qualified Person Declaration"},
                },
            },
            "1.16": {
                "title": "Traceability Table for Translations of the Product Information",
                "note": "Required for MR/DC procedures; lists all SmPC/PIL/label translations.",
            },
        },
    },

    # ── Nigeria (NAFDAC) Module 1 ────────────────────────────────────────────
    "nigeria": {
        "title": "Module 1: Administrative Information (Nigeria - NAFDAC)",
        "region": "Nigeria",
        "authority": "National Agency for Food and Drug Administration and Control (NAFDAC)",
        "harmonized": False,
        "children": {
            "1.0": {"title": "Comprehensive Table of Contents"},
            "1.1": {"title": "NAFDAC Application Form (PN Form 1)"},
            "1.2": {"title": "Cover Letter"},
            "1.3": {
                "title": "Labelling",
                "children": {
                    "1.3.1": {"title": "Summary of Product Characteristics (SmPC)"},
                    "1.3.2": {"title": "Mock-up Labels"},
                    "1.3.3": {"title": "Package Insert"},
                },
            },
            "1.4": {
                "title": "Regulatory Certificates",
                "children": {
                    "1.4.1": {"title": "GMP Certificate"},
                    "1.4.2": {"title": "Certificate of Pharmaceutical Product (CPP)"},
                    "1.4.3": {"title": "Free Sale Certificate"},
                },
            },
            "1.5": {"title": "Patent and Exclusivity Information"},
            "1.6": {"title": "Environmental Risk Assessment"},
            "1.7": {"title": "Pediatric Administrative Information"},
            "1.8": {
                "title": "Pharmacovigilance",
                "children": {
                    "1.8.1": {"title": "Risk Management Plan"},
                    "1.8.2": {"title": "Pharmacovigilance System Summary"},
                },
            },
            "1.9": {"title": "Fee Payment Evidence"},
            "1.10": {"title": "Power of Attorney / Local Agent Authorization"},
            "1.11": {"title": "Company Incorporation Certificate"},
            "1.12": {"title": "Reference Product Information (for generics)"},
            "1.13": {"title": "Previous Submissions and Correspondence"},
            "1.14": {"title": "Other Administrative Documents"},
        },
    },

    # ── South Africa (SAHPRA) Module 1 ──────────────────────────────────────
    "south africa": {
        "title": "Module 1: Administrative Information (South Africa - SAHPRA)",
        "region": "South Africa",
        "authority": "South African Health Products Regulatory Authority (SAHPRA)",
        "harmonized": False,
        "children": {
            "1.0": {"title": "Comprehensive Table of Contents"},
            "1.1": {"title": "SAHPRA Application Form (CC1 / CC2)"},
            "1.2": {"title": "Cover Letter"},
            "1.3": {
                "title": "Labelling and Product Information",
                "children": {
                    "1.3.1": {"title": "Professional Information (PI)"},
                    "1.3.2": {"title": "Patient Information Leaflet (PIL)"},
                    "1.3.3": {"title": "Labelling Artwork"},
                },
            },
            "1.4": {
                "title": "Regulatory Certificates",
                "children": {
                    "1.4.1": {"title": "GMP Certificate of Manufacturer"},
                    "1.4.2": {"title": "Certificate of Pharmaceutical Product (CPP)"},
                    "1.4.3": {"title": "Proof of Registration in Country of Origin"},
                },
            },
            "1.5": {"title": "Section 21 Authorization (if applicable)"},
            "1.6": {"title": "Scheduling Motivation"},
            "1.7": {"title": "Environmental Risk Assessment"},
            "1.8": {
                "title": "Pharmacovigilance",
                "children": {
                    "1.8.1": {"title": "Risk Management Plan (RMP)"},
                    "1.8.2": {"title": "Pharmacovigilance System Summary"},
                },
            },
            "1.9": {"title": "Pediatric Information"},
            "1.10": {"title": "Patent and Data Exclusivity Declaration"},
            "1.11": {"title": "Local Agent Authorization"},
            "1.12": {"title": "Previous Submissions and Correspondence"},
        },
    },

    # ── Ghana (FDA Ghana) Module 1 ───────────────────────────────────────────
    "ghana": {
        "title": "Module 1: Administrative Information (Ghana - FDA)",
        "region": "Ghana",
        "authority": "Food and Drugs Authority Ghana (FDA)",
        "harmonized": False,
        "children": {
            "1.0": {"title": "Comprehensive Table of Contents"},
            "1.1": {"title": "FDA Ghana Application Form"},
            "1.2": {"title": "Cover Letter"},
            "1.3": {
                "title": "Labelling",
                "children": {
                    "1.3.1": {"title": "Summary of Product Characteristics (SmPC)"},
                    "1.3.2": {"title": "Mock-up Labels"},
                    "1.3.3": {"title": "Package Insert / PIL"},
                },
            },
            "1.4": {
                "title": "Regulatory Certificates",
                "children": {
                    "1.4.1": {"title": "GMP Certificate"},
                    "1.4.2": {"title": "Certificate of Pharmaceutical Product (CPP)"},
                    "1.4.3": {"title": "Free Sale Certificate"},
                },
            },
            "1.5": {"title": "Environmental Risk Assessment"},
            "1.6": {"title": "Pharmacovigilance Plan"},
            "1.7": {"title": "Pediatric Information"},
            "1.8": {"title": "Power of Attorney / Local Representative Authorization"},
            "1.9": {"title": "Fee Payment Receipt"},
            "1.10": {"title": "Other Administrative Documents"},
        },
    },

    # ── Ethiopia (EFDA) Module 1 ─────────────────────────────────────────────
    "ethiopia": {
        "title": "Module 1: Administrative Information (Ethiopia - EFDA)",
        "region": "Ethiopia",
        "authority": "Ethiopian Food and Drug Authority (EFDA)",
        "harmonized": False,
        "children": {
            "1.0": {"title": "Comprehensive Table of Contents"},
            "1.1": {"title": "EFDA Application Form"},
            "1.2": {"title": "Cover Letter"},
            "1.3": {
                "title": "Labelling",
                "children": {
                    "1.3.1": {"title": "Summary of Product Characteristics (SmPC)"},
                    "1.3.2": {"title": "Mock-up Labels"},
                    "1.3.3": {"title": "Patient Information Leaflet"},
                },
            },
            "1.4": {
                "title": "Regulatory Certificates",
                "children": {
                    "1.4.1": {"title": "GMP Certificate"},
                    "1.4.2": {"title": "Certificate of Pharmaceutical Product (CPP)"},
                    "1.4.3": {"title": "Free Sale Certificate"},
                },
            },
            "1.5": {"title": "Environmental Risk Assessment"},
            "1.6": {"title": "Pharmacovigilance System Summary"},
            "1.7": {"title": "Pediatric Administrative Information"},
            "1.8": {"title": "Local Agent / Importer Authorization"},
            "1.9": {"title": "Business License of Importer"},
            "1.10": {"title": "Previous Submissions and Correspondence"},
        },
    },

    # ── Rwanda (Rwanda FDA) Module 1 ─────────────────────────────────────────
    "rwanda": {
        "title": "Module 1: Administrative Information (Rwanda - FDA)",
        "region": "Rwanda",
        "authority": "Rwanda Food and Drugs Authority (Rwanda FDA)",
        "harmonized": False,
        "children": {
            "1.0": {"title": "Comprehensive Table of Contents"},
            "1.1": {"title": "Rwanda FDA Application Form"},
            "1.2": {"title": "Cover Letter"},
            "1.3": {
                "title": "Labelling",
                "children": {
                    "1.3.1": {"title": "Summary of Product Characteristics (SmPC)"},
                    "1.3.2": {"title": "Mock-up Labels"},
                    "1.3.3": {"title": "Patient Information Leaflet"},
                },
            },
            "1.4": {
                "title": "Regulatory Certificates",
                "children": {
                    "1.4.1": {"title": "GMP Certificate"},
                    "1.4.2": {"title": "Certificate of Pharmaceutical Product (CPP)"},
                    "1.4.3": {"title": "Free Sale Certificate"},
                },
            },
            "1.5": {"title": "Environmental Risk Assessment"},
            "1.6": {"title": "Pharmacovigilance Plan"},
            "1.7": {"title": "Local Agent Authorization"},
            "1.8": {"title": "Fee Payment Evidence"},
            "1.9": {"title": "Other Administrative Documents"},
        },
    },
}


# ---------------------------------------------------------------------------
# MODULES 2-5 - Harmonized CTD (ICH M4 Standard)
# Identical across all regions; Module 1 carries regional differences
# ---------------------------------------------------------------------------

CTD_MODULE_2_TO_5 = [

    # -----------------------------------------------------------------------
    # MODULE 2 - CTD Summaries
    # Source: ICH M4Q (QOS + Module 3 summary), M4S (Nonclinical), M4E (Clinical)
    #
    # NOTE on 2.3 QOS sub-sections (per ICH M4Q):
    #   The QOS DOES have numbered sub-sections 2.3.S, 2.3.P, 2.3.A, 2.3.R
    #   that mirror Module 3's body of data. These appear in the CTD TOC
    #   (section 2.1) down to 3rd level (2.3.S) or 4th level (2.3.S.1).
    #   In eCTD they are INTERNAL HEADINGS within a single QOS document -
    #   NOT separate leaf-node files. One PDF is submitted for 2.3.
    #
    # NOTE on 2.4 and 2.5 (per M4S and M4E):
    #   Both have defined internal sub-headings. Single document each.
    # -----------------------------------------------------------------------
    {
        "module": 2,
        "title": "Module 2: Common Technical Document Summaries",
        "harmonized": True,
        "ich_guideline": "M4Q, M4S, M4E",
        "children": {

            "2.1": {"title": "CTD Table of Contents"},

            "2.2": {
                "title": "CTD Introduction",
                # Pharmacological class, mode of action, proposed clinical use.
                # Should not exceed one page (per ICH M4Q/M4S/M4E).
            },

            # -----------------------------------------------------------------
            # 2.3 Quality Overall Summary (QOS)
            # ICH M4Q: Follows scope and outline of Module 3 Body of Data.
            # Internal sections 2.3.S, 2.3.P, 2.3.A, 2.3.R are document
            # headings (not separate eCTD files). Max ~40 pages (80 for biotech).
            # -----------------------------------------------------------------
            "2.3": {
                "title": "Quality Overall Summary (QOS)",
                "ich_note": (
                    "Per ICH M4Q these sub-sections are INTERNAL HEADINGS "
                    "within a single QOS document, not separate eCTD leaf nodes."
                ),
                "children": {
                    "2.3.S": {
                        "title": "Drug Substance ",
                        "children": {
                            "2.3.S.1": {"title": "General Information "},
                            "2.3.S.2": {"title": "Manufacture "},
                            "2.3.S.3": {"title": "Characterization "},
                            "2.3.S.4": {"title": "Control of Drug Substance "},
                            "2.3.S.5": {"title": "Reference Standards or Materials "},
                            "2.3.S.6": {"title": "Container Closure System "},
                            "2.3.S.7": {"title": "Stability "},
                        },
                    },
                    "2.3.P": {
                        "title": "Drug Product [name, dosage form]",
                        "children": {
                            "2.3.P.1": {"title": "Description and Composition of the Drug Product"},
                            "2.3.P.2": {"title": "Pharmaceutical Development [name, dosage form]"},
                            "2.3.P.3": {"title": "Manufacture [name, dosage form]"},
                            "2.3.P.4": {"title": "Control of Excipients [name, dosage form]"},
                            "2.3.P.5": {"title": "Control of Drug Product [name, dosage form]"},
                            "2.3.P.6": {"title": "Reference Standards or Materials [name, dosage form]"},
                            "2.3.P.7": {"title": "Container Closure System [name, dosage form]"},
                            "2.3.P.8": {"title": "Stability [name, dosage form]"},
                        },
                    },
                    "2.3.A": {
                        "title": "Appendices",
                        "children": {
                            "2.3.A.1": {"title": "Facilities and Equipment"},
                            "2.3.A.2": {"title": "Adventitious Agents Safety Evaluation"},
                            "2.3.A.3": {"title": "Novel Excipients"},
                        },
                    },
                    "2.3.R": {
                        "title": "Regional Information",
                        # Brief description of regional info corresponding to 3.2.R
                    },
                },
            },

            # -----------------------------------------------------------------
            # 2.4 Nonclinical Overview
            # ICH M4S: Integrated critical assessment. Max ~30 pages.
            # Internal sub-headings (single document):
            # -----------------------------------------------------------------
            "2.4": {
                "title": "Nonclinical Overview",
                "children": {
                    "2.4.1": {"title": "Overview of the Nonclinical Testing Strategy"},
                    "2.4.2": {"title": "Pharmacology"},
                    "2.4.3": {"title": "Pharmacokinetics"},
                    "2.4.4": {"title": "Toxicology"},
                    "2.4.5": {"title": "Integrated Overview and Conclusions"},
                    "2.4.6": {"title": "List of Literature Citations"},
                },
            },

            # -----------------------------------------------------------------
            # 2.5 Clinical Overview
            # ICH M4E: Critical analysis of clinical data. ~30 pages.
            # Internal sub-headings (single document):
            # -----------------------------------------------------------------
            "2.5": {
                "title": "Clinical Overview",
                "children": {
                    "2.5.1": {"title": "Product Development Rationale"},
                    "2.5.2": {"title": "Overview of Biopharmaceutics"},
                    "2.5.3": {"title": "Overview of Clinical Pharmacology"},
                    "2.5.4": {"title": "Overview of Efficacy"},
                    "2.5.5": {"title": "Overview of Safety"},
                    "2.5.6": {"title": "Benefits and Risks Conclusions"},
                    "2.5.7": {"title": "References"},
                },
            },

            # -----------------------------------------------------------------
            # 2.6 Nonclinical Written and Tabulated Summaries
            # ICH M4S: Comprehensive factual synopsis. Total max ~100-150 pages.
            # -----------------------------------------------------------------
            "2.6": {
                "title": "Nonclinical Written and Tabulated Summaries",
                "children": {
                    "2.6.1": {
                        "title": "Introduction",
                        # Brief description of structure, pharmacologic properties,
                        # proposed clinical indication, dose, and duration of use
                    },
                    "2.6.2": {
                        "title": "Pharmacology Written Summary",
                        "children": {
                            "2.6.2.1":  {"title": "Brief Summary"},
                            "2.6.2.2":  {"title": "Primary Pharmacodynamics"},
                            "2.6.2.3":  {"title": "Secondary Pharmacodynamics"},
                            "2.6.2.4":  {"title": "Safety Pharmacology"},
                            "2.6.2.5":  {"title": "Pharmacodynamic Drug Interactions"},
                            "2.6.2.6":  {"title": "Discussion and Conclusions"},
                            "2.6.2.7":  {"title": "Tables and Figures"},
                        },
                    },
                    "2.6.3": {
                        "title": "Pharmacology Tabulated Summary",
                        # Tabulated format per Appendix B of ICH M4S
                    },
                    "2.6.4": {
                        "title": "Pharmacokinetics Written Summary",
                        "children": {
                            "2.6.4.1":  {"title": "Brief Summary"},
                            "2.6.4.2":  {"title": "Methods of Analysis"},
                            "2.6.4.3":  {"title": "Absorption"},
                            "2.6.4.4":  {"title": "Distribution"},
                            "2.6.4.5":  {"title": "Metabolism (Interspecies Comparison)"},
                            "2.6.4.6":  {"title": "Excretion"},
                            "2.6.4.7":  {"title": "Pharmacokinetic Drug Interactions"},
                            "2.6.4.8":  {"title": "Other Pharmacokinetic Studies"},
                            "2.6.4.9":  {"title": "Discussion and Conclusions"},
                            "2.6.4.10": {"title": "Tables and Figures"},
                        },
                    },
                    "2.6.5": {
                        "title": "Pharmacokinetics Tabulated Summary",
                        # Tabulated format per Appendix B of ICH M4S
                    },
                    "2.6.6": {
                        "title": "Toxicology Written Summary",
                        "children": {
                            "2.6.6.1":  {"title": "Brief Summary"},
                            "2.6.6.2":  {"title": "Single-Dose Toxicity"},
                            "2.6.6.3":  {"title": "Repeat-Dose Toxicity (including supportive toxicokinetic evaluation)"},
                            "2.6.6.4":  {"title": "Genotoxicity"},
                            "2.6.6.5":  {"title": "Carcinogenicity (including supportive toxicokinetic evaluations)"},
                            "2.6.6.6":  {"title": "Reproductive and Developmental Toxicity (including range-finding studies and supportive toxicokinetic evaluations)"},
                            "2.6.6.7":  {"title": "Local Tolerance"},
                            "2.6.6.8":  {"title": "Other Toxicity Studies (if available)"},
                            "2.6.6.9":  {"title": "Discussion and Conclusions"},
                            "2.6.6.10": {"title": "Tables and Figures"},
                        },
                    },
                    "2.6.7": {
                        "title": "Toxicology Tabulated Summary",
                        # Tabulated format per Appendix B of ICH M4S
                    },
                },
            },

            # -----------------------------------------------------------------
            # 2.7 Clinical Summary
            # ICH M4E: Detailed factual summarization of all clinical data.
            # -----------------------------------------------------------------
            "2.7": {
                "title": "Clinical Summary",
                "children": {
                    "2.7.1": {
                        "title": "Summary of Biopharmaceutic Studies and Associated Analytical Methods",
                        "children": {
                            "2.7.1.1": {"title": "Background and Overview"},
                            "2.7.1.2": {"title": "Summary of Results of Individual Studies"},
                            "2.7.1.3": {"title": "Comparison and Analyses of Results Across Studies"},
                            "2.7.1.4": {"title": "Appendix"},
                        },
                    },
                    "2.7.2": {
                        "title": "Summary of Clinical Pharmacology Studies",
                        "children": {
                            "2.7.2.1": {"title": "Background and Overview"},
                            "2.7.2.2": {"title": "Summary of Results of Individual Studies"},
                            "2.7.2.3": {"title": "Comparison and Analyses of Results Across Studies"},
                            "2.7.2.4": {"title": "Special Studies"},
                            "2.7.2.5": {"title": "Appendix"},
                        },
                    },
                    "2.7.3": {
                        "title": "Summary of Clinical Efficacy",
                        "children": {
                            "2.7.3.1": {"title": "Background and Overview of Clinical Efficacy"},
                            "2.7.3.2": {"title": "Summary of Results of Individual Studies"},
                            "2.7.3.3": {"title": "Comparison and Analyses of Results Across Studies"},
                            "2.7.3.4": {"title": "Analysis of Clinical Information Relevant to Dosing Recommendations"},
                            "2.7.3.5": {"title": "Persistence of Efficacy and/or Tolerance Effects"},
                            "2.7.3.6": {"title": "Appendix"},
                        },
                    },
                    "2.7.4": {
                        "title": "Summary of Clinical Safety",
                        "children": {
                            "2.7.4.1": {"title": "Exposure to the Drug"},
                            "2.7.4.2": {"title": "Adverse Events"},
                            "2.7.4.3": {"title": "Clinical Laboratory Evaluations"},
                            "2.7.4.4": {"title": "Vital Signs, Physical Findings, and Other Observations Related to Safety"},
                            "2.7.4.5": {"title": "Safety in Special Groups and Situations"},
                            "2.7.4.6": {"title": "Postmarketing Data"},
                            "2.7.4.7": {"title": "Appendix"},
                        },
                    },
                    "2.7.5": {"title": "References"},
                    "2.7.6": {"title": "Synopses of Individual Studies"},
                },
            },
        },
    },

    # -----------------------------------------------------------------------
    # MODULE 3 - Quality (Chemistry, Manufacturing and Controls - CMC)
    # Source: ICH M4Q (R1) - https://www.fda.gov/media/71581/download
    # -----------------------------------------------------------------------
    {
        "module": 3,
        "title": "Module 3: Quality (Chemistry, Manufacturing and Controls)",
        "harmonized": True,
        "ich_guideline": "M4Q (R1)",
        "children": {
            "3.1": {"title": "Module 3 Table of Contents"},
            "3.2": {
                "title": "Body of Data",
                "children": {

                    # ---------------------------------------------------------
                    # 3.2.S - Drug Substance (API)
                    # Repeat entire S section for each drug substance / manufacturer
                    # ---------------------------------------------------------
                    "3.2.S": {
                        "title": "Drug Substance ",
                        "children": {
                            "3.2.S.1": {
                                "title": "General Information ",
                                "children": {
                                    "3.2.S.1.1": {"title": "Nomenclature "},
                                    "3.2.S.1.2": {"title": "Structure "},
                                    "3.2.S.1.3": {"title": "General Properties "},
                                },
                            },
                            "3.2.S.2": {
                                "title": "Manufacture ",
                                "children": {
                                    "3.2.S.2.1": {"title": "Manufacturer(s) "},
                                    "3.2.S.2.2": {"title": "Description of Manufacturing Process and Process Controls "},
                                    "3.2.S.2.3": {"title": "Control of Materials "},
                                    "3.2.S.2.4": {"title": "Controls of Critical Steps and Intermediates "},
                                    "3.2.S.2.5": {"title": "Process Validation and/or Evaluation "},
                                    "3.2.S.2.6": {"title": "Manufacturing Process Development "},
                                },
                            },
                            "3.2.S.3": {
                                "title": "Characterization ",
                                "children": {
                                    "3.2.S.3.1": {"title": "Elucidation of Structure and Other Characteristics "},
                                    "3.2.S.3.2": {"title": "Impurities "},
                                },
                            },
                            "3.2.S.4": {
                                "title": "Control of Drug Substance ",
                                "children": {
                                    "3.2.S.4.1": {"title": "Specification "},
                                    "3.2.S.4.2": {"title": "Analytical Procedures "},
                                    "3.2.S.4.3": {"title": "Validation of Analytical Procedures "},
                                    "3.2.S.4.4": {"title": "Batch Analyses "},
                                    "3.2.S.4.5": {"title": "Justification of Specification "},
                                },
                            },
                            "3.2.S.5": {"title": "Reference Standards or Materials "},
                            "3.2.S.6": {"title": "Container Closure System "},
                            "3.2.S.7": {
                                "title": "Stability ",
                                "children": {
                                    "3.2.S.7.1": {"title": "Stability Summary and Conclusions "},
                                    "3.2.S.7.2": {"title": "Postapproval Stability Protocol and Stability Commitment "},
                                    "3.2.S.7.3": {"title": "Stability Data "},
                                },
                            },
                        },
                    },

                    # ---------------------------------------------------------
                    # 3.2.P - Drug Product (Finished Dosage Form)
                    # Repeat entire P section for each dosage form
                    # ---------------------------------------------------------
                    "3.2.P": {
                        "title": "Drug Product [name, dosage form]",
                        "children": {
                            "3.2.P.1": {"title": "Description and Composition of the Drug Product [name, dosage form]"},
                            "3.2.P.2": {
                                "title": "Pharmaceutical Development [name, dosage form]",
                                "children": {
                                    "3.2.P.2.1": {"title": "Components of the Drug Product [name, dosage form]"},
                                    "3.2.P.2.2": {"title": "Drug Product [name, dosage form]"},
                                    "3.2.P.2.3": {"title": "Manufacturing Process Development [name, dosage form]"},
                                    "3.2.P.2.4": {"title": "Container Closure System [name, dosage form]"},
                                    "3.2.P.2.5": {"title": "Microbiological Attributes [name, dosage form]"},
                                    "3.2.P.2.6": {"title": "Compatibility [name, dosage form]"},
                                },
                            },
                            "3.2.P.3": {
                                "title": "Manufacture [name, dosage form]",
                                "children": {
                                    "3.2.P.3.1": {"title": "Manufacturer(s) [name, dosage form]"},
                                    "3.2.P.3.2": {"title": "Batch Formula [name, dosage form]"},
                                    "3.2.P.3.3": {"title": "Description of Manufacturing Process and Process Controls [name, dosage form]"},
                                    "3.2.P.3.4": {"title": "Controls of Critical Steps and Intermediates [name, dosage form]"},
                                    "3.2.P.3.5": {"title": "Process Validation and/or Evaluation [name, dosage form]"},
                                },
                            },
                            "3.2.P.4": {
                                "title": "Control of Excipients [name, dosage form]",
                                "children": {
                                    "3.2.P.4.1": {"title": "Specifications [name, dosage form]"},
                                    "3.2.P.4.2": {"title": "Analytical Procedures [name, dosage form]"},
                                    "3.2.P.4.3": {"title": "Validation of Analytical Procedures [name, dosage form]"},
                                    "3.2.P.4.4": {"title": "Justification of Specifications [name, dosage form]"},
                                    "3.2.P.4.5": {"title": "Excipients of Human or Animal Origin [name, dosage form]"},
                                    "3.2.P.4.6": {"title": "Novel Excipients [name, dosage form]"},
                                    # NOTE: 3.2.P.4.5 and 3.2.P.4.6 were missing in previous version
                                },
                            },
                            "3.2.P.5": {
                                "title": "Control of Drug Product [name, dosage form]",
                                "children": {
                                    "3.2.P.5.1": {"title": "Specification(s) [name, dosage form]"},
                                    "3.2.P.5.2": {"title": "Analytical Procedures [name, dosage form]"},
                                    "3.2.P.5.3": {"title": "Validation of Analytical Procedures [name, dosage form]"},
                                    "3.2.P.5.4": {"title": "Batch Analyses [name, dosage form]"},
                                    "3.2.P.5.5": {"title": "Characterization of Impurities [name, dosage form]"},
                                    "3.2.P.5.6": {"title": "Justification of Specification(s) [name, dosage form]"},
                                },
                            },
                            "3.2.P.6": {"title": "Reference Standards or Materials [name, dosage form]"},
                            "3.2.P.7": {"title": "Container Closure System [name, dosage form]"},
                            "3.2.P.8": {
                                "title": "Stability [name, dosage form]",
                                "children": {
                                    "3.2.P.8.1": {"title": "Stability Summary and Conclusion [name, dosage form]"},
                                    "3.2.P.8.2": {"title": "Postapproval Stability Protocol and Stability Commitment [name, dosage form]"},
                                    "3.2.P.8.3": {"title": "Stability Data [name, dosage form]"},
                                },
                            },
                        },
                    },

                    # ---------------------------------------------------------
                    # 3.2.A - Appendices
                    # ---------------------------------------------------------
                    "3.2.A": {
                        "title": "Appendices",
                        "children": {
                            "3.2.A.1": {
                                "title": "Facilities and Equipment",
                                # Required for biotech; diagram of manufacturing flow
                            },
                            "3.2.A.2": {
                                "title": "Adventitious Agents Safety Evaluation",
                                # Viral and non-viral adventitious agents risk assessment
                            },
                            "3.2.A.3": {
                                "title": "Novel Excipients",
                                # Full details for excipients used for first time
                            },
                        },
                    },

                    # ---------------------------------------------------------
                    # 3.2.R - Regional Information
                    # Per M4Q examples: Executed Batch Records (US only),
                    # Method Validation Package (US only),
                    # Comparability Protocols (US only),
                    # Process Validation Scheme for Drug Product (EU only),
                    # Medical Device (EU only)
                    # ---------------------------------------------------------
                    "3.2.R": {
                        "title": "Regional Information",
                        "children": {
                            "3.2.R.1": {
                                "title": "Production Documentation",
                                # e.g. Executed Batch Records (US requirement)
                            },
                        },
                    },
                },
            },
            "3.3": {
                "title": "Literature References",
                # Key literature referenced in Module 3 body of data
            },
        },
    },

    # -----------------------------------------------------------------------
    # MODULE 4 - Nonclinical Study Reports
    # Source: ICH M4S - https://www.fda.gov/media/71628/download
    # -----------------------------------------------------------------------
    {
        "module": 4,
        "title": "Module 4: Nonclinical Study Reports",
        "harmonized": True,
        "ich_guideline": "M4S",
        "children": {
            "4.1": {"title": "Module 4 Table of Contents"},
            "4.2": {
                "title": "Study Reports",
                "children": {
                    "4.2.1": {
                        "title": "Pharmacology",
                        "children": {
                            "4.2.1.1": {"title": "Primary Pharmacodynamics"},
                            "4.2.1.2": {"title": "Secondary Pharmacodynamics"},
                            "4.2.1.3": {"title": "Safety Pharmacology"},
                            "4.2.1.4": {"title": "Pharmacodynamic Drug Interactions"},
                        },
                    },
                    "4.2.2": {
                        "title": "Pharmacokinetics",
                        "children": {
                            "4.2.2.1": {"title": "Analytical Methods and Validation Reports (if separate)"},
                            "4.2.2.2": {"title": "Absorption"},
                            "4.2.2.3": {"title": "Distribution"},
                            "4.2.2.4": {"title": "Metabolism"},
                            "4.2.2.5": {"title": "Excretion"},
                            "4.2.2.6": {"title": "Pharmacokinetic Drug Interactions (Nonclinical)"},
                            "4.2.2.7": {"title": "Other Pharmacokinetic Studies"},
                        },
                    },
                    "4.2.3": {
                        "title": "Toxicology",
                        "children": {
                            "4.2.3.1": {"title": "Single-Dose Toxicity"},
                            "4.2.3.2": {"title": "Repeat-Dose Toxicity"},
                            "4.2.3.3": {"title": "Genotoxicity"},
                            "4.2.3.4": {"title": "Carcinogenicity"},
                            "4.2.3.5": {
                                "title": "Reproductive and Developmental Toxicity",
                                "children": {
                                    "4.2.3.5.1": {"title": "Fertility and Early Embryonic Development"},
                                    "4.2.3.5.2": {"title": "Embryo-Fetal Development"},
                                    "4.2.3.5.3": {"title": "Prenatal and Postnatal Development (including Maternal Function)"},
                                    "4.2.3.5.4": {"title": "Studies in which Offspring (Juvenile Animals) are Dosed and/or Further Evaluated"},
                                },
                            },
                            "4.2.3.6": {"title": "Local Tolerance"},
                            "4.2.3.7": {
                                "title": "Other Toxicity Studies (if available)",
                                "children": {
                                    "4.2.3.7.1": {"title": "Antigenicity"},
                                    "4.2.3.7.2": {"title": "Immunotoxicity"},
                                    "4.2.3.7.3": {"title": "Mechanistic Studies (if not included above)"},
                                    "4.2.3.7.4": {"title": "Dependence"},
                                    "4.2.3.7.5": {"title": "Metabolites"},
                                    "4.2.3.7.6": {"title": "Impurities"},
                                    "4.2.3.7.7": {"title": "Other"},
                                },
                            },
                        },
                    },
                },
            },
            "4.3": {"title": "Literature References"},
        },
    },

    # -----------------------------------------------------------------------
    # MODULE 5 - Clinical Study Reports
    # Source: ICH M4E - https://www.fda.gov/media/71610/download
    # -----------------------------------------------------------------------
    {
        "module": 5,
        "title": "Module 5: Clinical Study Reports",
        "harmonized": True,
        "ich_guideline": "M4E",
        "children": {
            "5.1": {"title": "Module 5 Table of Contents"},
            "5.2": {"title": "Tabular Listing of All Clinical Studies"},
            "5.3": {
                "title": "Clinical Study Reports",
                "children": {
                    "5.3.1": {
                        "title": "Reports of Biopharmaceutic Studies",
                        "children": {
                            "5.3.1.1": {"title": "Bioavailability (BA) Study Reports"},
                            "5.3.1.2": {"title": "Comparative BA and Bioequivalence (BE) Study Reports"},
                            "5.3.1.3": {"title": "In Vitro - In Vivo Correlation Study Reports"},
                            "5.3.1.4": {"title": "Reports of Bioanalytical and Analytical Methods for Human Studies"},
                        },
                    },
                    "5.3.2": {
                        "title": "Reports of Studies Pertinent to Pharmacokinetics Using Human Biomaterials",
                        "children": {
                            "5.3.2.1": {"title": "Plasma Protein Binding Study Reports"},
                            "5.3.2.2": {"title": "Reports of Hepatic Metabolism and Drug Interaction Studies"},
                            "5.3.2.3": {"title": "Reports of Studies Using Other Human Biomaterials"},
                        },
                    },
                    "5.3.3": {
                        "title": "Reports of Human Pharmacokinetic (PK) Studies",
                        "children": {
                            "5.3.3.1": {"title": "Healthy Subject PK and Initial Tolerability Study Reports"},
                            "5.3.3.2": {"title": "Patient PK and Initial Tolerability Study Reports"},
                            "5.3.3.3": {"title": "Intrinsic Factor PK Study Reports"},
                            "5.3.3.4": {"title": "Extrinsic Factor PK Study Reports"},
                            "5.3.3.5": {"title": "Population PK Study Reports"},
                        },
                    },
                    "5.3.4": {
                        "title": "Reports of Human Pharmacodynamic (PD) Studies",
                        "children": {
                            "5.3.4.1": {"title": "Healthy Subject PD and PK/PD Study Reports"},
                            "5.3.4.2": {"title": "Patient PD and PK/PD Study Reports"},
                        },
                    },
                    "5.3.5": {
                        "title": "Reports of Efficacy and Safety Studies",
                        "children": {
                            "5.3.5.1": {"title": "Study Reports of Controlled Clinical Studies Pertinent to the Claimed Indication"},
                            "5.3.5.2": {"title": "Study Reports of Uncontrolled Clinical Studies"},
                            "5.3.5.3": {"title": "Reports of Analyses of Data from More than One Study (Including Any Formal Integrated Analyses, Meta-Analyses, and Bridging Analyses)"},
                            "5.3.5.4": {"title": "Other Study Reports"},
                            # NOTE: Correct ICH M4E title is "Other Study Reports"
                        },
                    },
                    "5.3.6": {
                        "title": "Reports of Postmarketing Experience",
                        # Applicable for line extensions / supplemental applications
                    },
                    "5.3.7": {
                        "title": "Case Report Forms and Individual Patient Listings",
                        # Required for certain pivotal studies per regional guidance
                    },
                },
            },
            "5.4": {"title": "Literature References"},
        },
    },
]


# ---------------------------------------------------------------------------
# UTILITY: Flat index of all CTD sections for lookup / validation
# ---------------------------------------------------------------------------

def _flatten(node: dict, prefix: str = "") -> dict:
    """Recursively flatten a CTD node dict into {section_number: title}.

    Keys may be plain numbers ("1.1") or alphanumeric ("3.2.S", "2.3.S.1").
    When a prefix already ends with the key (dotted keys), we don't double-prefix.
    """
    result = {}
    for key, value in node.items():
        # Build the full section number:
        #   - If no prefix yet, the key IS the full section number.
        #   - If prefix exists and key starts with prefix, use key as-is
        #     (handles cases like prefix="2.3", key="2.3.S").
        #   - Otherwise append key to prefix with a dot.
        if not prefix:
            full_key = key
        elif key.startswith(prefix + ".") or key.startswith(prefix):
            full_key = key
        else:
            full_key = f"{prefix}.{key}"

        if isinstance(value, dict):
            result[full_key] = value.get("title", "")
            children = value.get("children", {})
            if children:
                result.update(_flatten(children, prefix=full_key))
    return result


def get_flat_index(region: str = None) -> dict:
    """
    Return a flat dict of {section: title} for all CTD modules.

    Args:
        region: One of 'uganda', 'kenya', 'tanzania', 'who', 'eu',
                'nigeria', 'south_africa', 'ghana', 'ethiopia', 'rwanda'
                (for Module 1). If None, Module 1 is skipped.

    Returns:
        dict mapping section strings to titles.

    Example:
        >>> idx = get_flat_index("uganda")
        >>> idx["3.2.S.4.1"]
        'Specification '
        >>> idx["5.3.5.4"]
        'Other Study Reports'
    """
    index = {}
    if region and region in CTD_MODULE_1:
        m1 = CTD_MODULE_1[region]
        index.update(_flatten(m1.get("children", {})))
    for module in CTD_MODULE_2_TO_5:
        index.update(_flatten(module.get("children", {})))
    return index