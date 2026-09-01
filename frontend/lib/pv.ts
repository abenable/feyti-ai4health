import type {
  ADRReport,
  PVDrug,
  PVMinimumCriteriaCheck,
  PVPatient,
  PVReportDraft,
} from "@/lib/types";

export const PV_SERIOUSNESS_OPTIONS = [
  "death",
  "life_threatening",
  "hospitalization",
  "disability",
  "congenital",
  "other",
] as const;

export const PV_SEVERITY_OPTIONS = [
  { value: "mild", label: "Mild" },
  { value: "moderate", label: "Moderate" },
  { value: "severe", label: "Severe" },
  { value: "life_threatening", label: "Life-threatening" },
  { value: "fatal", label: "Fatal" },
] as const;

export const PV_CAUSALITY_OPTIONS = [
  { value: "certain", label: "Certain" },
  { value: "probable", label: "Probable" },
  { value: "possible", label: "Possible" },
  { value: "unlikely", label: "Unlikely" },
  { value: "conditional", label: "Conditional" },
  { value: "unassessable", label: "Unassessable" },
] as const;

export const PV_OUTCOME_OPTIONS = [
  { value: "recovered", label: "Recovered" },
  { value: "recovering", label: "Recovering" },
  { value: "not_recovered", label: "Not recovered" },
  { value: "fatal", label: "Fatal" },
  { value: "unknown", label: "Unknown" },
] as const;

export const PV_ACTION_OPTIONS = [
  { value: "withdrawn", label: "Drug withdrawn" },
  { value: "dose_reduced", label: "Dose reduced" },
  { value: "dose_increased", label: "Dose increased" },
  { value: "dose_not_changed", label: "Dose not changed" },
  { value: "not_applicable", label: "Not applicable" },
  { value: "unknown", label: "Unknown" },
] as const;

export function createEmptyPVReport(productName = ""): ADRReport {
  const now = new Date().toISOString();
  return {
    report_id: "",
    worldwide_unique_id: "",
    case_version: 1,
    case_report_type: "initial",
    organization: "",
    product_name: productName,
    drug: {
      name: productName,
      batch_number: "",
      dose_text: "",
      route_of_administration: "",
      indication: "",
      action_taken: null,
      therapy_start_date: null,
      therapy_end_date: null,
    },
    reaction_pt_code: null,
    reaction_pt_name: null,
    reaction_meddra_term: "",
    reaction_description: "",
    reaction_start_date: null,
    seriousness_criteria: [],
    is_serious: false,
    severity: null,
    causality: null,
    outcome: null,
    patient: {
      identifier: "",
      age: null,
      age_group: "",
      sex: "",
      initials: "",
      dob: null,
    },
    reporter_name: "",
    reporter_email: "",
    reporter_phone: "",
    reporter_organisation: "",
    reporter_qualification: "",
    reporter_country: "",
    expectedness: null,
    expectedness_rationale: "",
    expectedness_assessed_by: "",
    expectedness_assessed_at: null,
    expectedness_rsi_version: "",
    is_susar: false,
    meddra: null,
    meddra_version: null,
    follow_ups: [],
    status: "draft",
    first_received_date: now.slice(0, 10),
    nullification_reason: "",
    created_at: now,
    updated_at: now,
  };
}

function mergePatient(current: PVPatient | null | undefined, draft: PVPatient | null | undefined): PVPatient {
  const next: PVPatient = { ...current };
  if (!draft) return next;
  (Object.keys(draft) as (keyof PVPatient)[]).forEach((key) => {
    const value = draft[key];
    if (value !== null && value !== undefined) next[key] = value as never;
  });
  return next;
}

function mergeDrug(current: PVDrug | null | undefined, draft: PVDrug | null | undefined): PVDrug {
  const next: PVDrug = { ...current };
  if (!draft) return next;
  (Object.keys(draft) as (keyof PVDrug)[]).forEach((key) => {
    const value = draft[key];
    if (value !== null && value !== undefined) next[key] = value as never;
  });
  return next;
}

export function applyPVReportDraft(report: ADRReport, draft: PVReportDraft): ADRReport {
  const next: ADRReport = { ...report };
  if (draft.product_name) {
    next.product_name = draft.product_name;
    if (!next.drug?.name) next.drug = { ...next.drug, name: draft.product_name };
  }
  if (draft.patient) next.patient = mergePatient(next.patient, draft.patient);
  if (draft.drug) next.drug = mergeDrug(next.drug, draft.drug);
  if (draft.reaction_meddra_term) next.reaction_meddra_term = draft.reaction_meddra_term;
  if (draft.reaction_description) next.reaction_description = draft.reaction_description;
  if (draft.reaction_start_date) next.reaction_start_date = draft.reaction_start_date;
  if (draft.seriousness_criteria?.length) next.seriousness_criteria = draft.seriousness_criteria;
  if (draft.is_serious !== null && draft.is_serious !== undefined) next.is_serious = draft.is_serious;
  if (draft.severity) next.severity = draft.severity;
  if (draft.causality) next.causality = draft.causality;
  if (draft.outcome) next.outcome = draft.outcome;
  if (draft.reporter_name) next.reporter_name = draft.reporter_name;
  if (draft.reporter_email) next.reporter_email = draft.reporter_email;
  if (draft.reporter_phone) next.reporter_phone = draft.reporter_phone;
  if (draft.reporter_organisation) next.reporter_organisation = draft.reporter_organisation;
  if (draft.reporter_qualification) next.reporter_qualification = draft.reporter_qualification;
  if (draft.reporter_country) next.reporter_country = draft.reporter_country;
  if (draft.first_received_date) next.first_received_date = draft.first_received_date;
  if (draft.worldwide_unique_id) next.worldwide_unique_id = draft.worldwide_unique_id;
  if (draft.organization) next.organization = draft.organization;
  return next;
}

export function evaluatePVMinimumCriteria(report: ADRReport): PVMinimumCriteriaCheck {
  const patient = report.patient;
  const patientPresent = Boolean(
    patient?.identifier ||
      patient?.age ||
      patient?.age_group ||
      patient?.sex ||
      patient?.initials ||
      patient?.dob
  );
  const reporterPresent = Boolean(
    report.reporter_name ||
      report.reporter_email ||
      report.reporter_phone ||
      report.reporter_organisation
  );
  const productPresent = Boolean(report.product_name || report.drug?.name);
  const reactionPresent = Boolean(report.reaction_meddra_term || report.reaction_description);

  const missing: string[] = [];
  if (!patientPresent) missing.push("patient");
  if (!reporterPresent) missing.push("reporter");
  if (!productPresent) missing.push("product");
  if (!reactionPresent) missing.push("reaction");

  const labels: Record<string, string> = {
    patient: "an identifiable patient",
    reporter: "an identifiable reporter",
    product: "a suspect medicinal product",
    reaction: "a suspect adverse reaction",
  };
  const description = missing.length
    ? `Not yet a valid ICSR — still needs ${missing.map((key) => labels[key]).join(", ")}.`
    : "";

  return { patient: patientPresent, reporter: reporterPresent, product: productPresent, reaction: reactionPresent, missing, description };
}
