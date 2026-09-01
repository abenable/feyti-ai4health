from __future__ import annotations

from datetime import date
from typing import Literal, List, Optional

from pydantic import BaseModel, Field

# Literals for various enumerations used in pharmacovigilance reports
SeverityLiteral = Literal["mild", "moderate", "severe"]
CausalityLiteral = Literal["certain", "probable", "possible", "unlikely", "unassessable"]
OutcomeLiteral = Literal["recovered", "recovering", "not_recovered", "fatal", "unknown"]
ActionLiteral = Literal["withdrawn", "dose_reduced", "dose_increased", "dose_not_changed", "unknown", "not_applicable"]
StatusLiteral = Literal["draft", "submitted", "nullified", "followup"]

class Patient(BaseModel):
    identifier: Optional[str] = None
    age: Optional[int] = None
    age_group: Optional[str] = None
    sex: Optional[str] = None
    initials: Optional[str] = None
    dob: Optional[date] = None

class Drug(BaseModel):
    name: str
    batch_number: Optional[str] = None
    dose_text: Optional[str] = None
    route_of_administration: Optional[str] = None
    indication: Optional[str] = None
    action_taken: Optional[ActionLiteral] = None
    therapy_start_date: Optional[date] = None
    therapy_end_date: Optional[date] = None

class MedDRACoding(BaseModel):
    pt_code: str
    pt_name: str
    version: Optional[str] = None

class FollowUp(BaseModel):
    report_id: str
    date: date
    description: Optional[str] = None

class ExpectedReaction(BaseModel):
    pt_code: str
    pt_name: str
    severity: Optional[SeverityLiteral] = None
    causality: Optional[CausalityLiteral] = None
    notes: Optional[str] = None

class MinimumCriteriaCheck(BaseModel):
    patient: bool
    reporter: bool
    product: bool
    reaction: bool
    missing: List[str] = Field(default_factory=list)
    description: str = ""

class ADRReport(BaseModel):
    # Core identifiers
    report_id: str
    worldwide_unique_id: Optional[str] = None
    case_version: int = 1
    case_report_type: Literal["initial", "followup", "nullification"] = "initial"
    organization: Optional[str] = None
    # Product / drug
    product_name: str
    drug: Optional[Drug] = None
    # Reaction
    reaction_pt_code: Optional[str] = None
    reaction_pt_name: Optional[str] = None
    reaction_meddra_term: Optional[str] = None
    reaction_description: Optional[str] = None
    reaction_start_date: Optional[date] = None
    seriousness_criteria: List[str] = Field(default_factory=list)
    is_serious: bool = False
    outcome: Optional[OutcomeLiteral] = None
    # Patient
    patient: Optional[Patient] = None
    # Reporter details (simplified)
    reporter_name: Optional[str] = None
    reporter_email: Optional[str] = None
    reporter_phone: Optional[str] = None
    reporter_organisation: Optional[str] = None
    reporter_qualification: Optional[str] = None
    reporter_country: Optional[str] = None
    # Expectedness / SUSAR handling
    expectedness: Optional[Literal["expected", "unexpected", "not_assessable"]] = None
    expectedness_rationale: Optional[str] = None
    expectedness_assessed_by: Optional[str] = None
    expectedness_assessed_at: Optional[date] = None
    expectedness_rsi_version: Optional[str] = None
    is_susar: bool = False
    # Follow‑ups
    follow_ups: List[FollowUp] = Field(default_factory=list)
    # Status tracking
    status: StatusLiteral = "draft"
