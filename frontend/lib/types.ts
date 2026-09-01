// Shared response/request types for the Feyti API. Single source of truth —
// previously duplicated across app/page.tsx, app/review/page.tsx, app/chat/page.tsx.

export type ReviewStatusValue = "draft" | "edited" | "approved";

export interface DossierSummary {
  id: string;
  name: string;
  product_name: string;
  created_at: string;
  filed: number;
  approved: number;
}

export interface ProductContext {
  product_name: string;
  active_ingredient: string;
  dosage_form: string;
  strength: string;
  applicant: string;
  market: string;
}

export const EMPTY_CONTEXT: ProductContext = {
  product_name: "",
  active_ingredient: "",
  dosage_form: "",
  strength: "",
  applicant: "",
  market: "",
};

export interface Classification {
  section_path: string;
  title: string;
  module: string;
  confidence: number;
  justification?: string;
}

export interface ExtractedField {
  label: string;
  value: string;
  page: number;
  confidence: number;
}

export interface ProcessResponse {
  filename: string;
  extracted_chars: number;
  ocr_used: boolean;
  classification: Classification;
  summary?: string;
  key_points?: string[];
  fields?: ExtractedField[];
  dossier_folder: string;
  section_path: string;
  stem: string;
}

export interface DossierTreeSection {
  section_path: string;
  title: string;
  documents: { name: string; confidence: number; uploaded_at: string }[];
}

export interface DossierTree {
  module: string;
  sections: DossierTreeSection[];
}

export interface PlanDoc {
  section_path: string;
  stem: string;
  filename: string;
  title: string;
  status: ReviewStatusValue;
  updated_at: string;
}

export interface PlanSection {
  path: string;
  title: string;
  status: "approved" | "in_review" | "empty";
  documents: PlanDoc[];
}

export interface PlanModule {
  module: string;
  sections: PlanSection[];
}

export interface DocumentMeta {
  filename?: string;
  section_path?: string;
  title?: string;
  module?: string;
  confidence?: number;
  justification?: string;
  summary?: string;
  key_points?: string[];
  extracted_chars?: number;
  had_ocr?: boolean;
  fields?: ExtractedField[];
  uploaded_at?: string;
}

export interface DocumentDetail {
  markdown: string;
  status: ReviewStatusValue;
  meta: DocumentMeta;
}

// /generate and /feedback return only markdown + status (no meta).
export type GenerateResult = Pick<DocumentDetail, "markdown" | "status">;

export interface NewSectionResponse {
  section_path: string;
  stem: string;
  markdown: string;
  status: ReviewStatusValue;
}

export interface ReclassifyResponse {
  section_path: string;
  stem: string;
}

export interface SourcePage {
  page: number;
  text: string;
  is_ocr: boolean;
}

export interface SourceDoc {
  pages: SourcePage[];
  had_ocr: boolean;
  extracted_chars: number;
  filename: string;
}

export interface ValidationCheck {
  id: string;
  level: "error" | "warn";
  message: string;
  line: number | null;
}

export interface ValidationReport {
  checks: ValidationCheck[];
  open_gaps: number;
  score: number;
  narrative: string;
}

export interface ModuleReadiness {
  module: string;
  approved: number;
  in_review: number;
  empty: number;
  drafted: number;
}

export interface ReadinessReport {
  score: number;
  verdict_label: "ready" | "nearly" | "not_ready";
  totals: {
    approved: number;
    in_review: number;
    empty: number;
    engaged: number;
    catalogue: number;
  };
  open_gaps: number;
  modules: ModuleReadiness[];
  narrative: string;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

// ── Pharmacovigilance / ADR ──────────────────────────────────────────────────

export type PVSeverity =
  | "mild"
  | "moderate"
  | "severe"
  | "life_threatening"
  | "fatal";

export type PVCausality =
  | "certain"
  | "probable"
  | "possible"
  | "unlikely"
  | "conditional"
  | "unassessable";

export type PVOutcome =
  | "recovered"
  | "recovering"
  | "not_recovered"
  | "fatal"
  | "unknown";

export type PVActionTaken =
  | "withdrawn"
  | "dose_reduced"
  | "dose_increased"
  | "dose_not_changed"
  | "unknown"
  | "not_applicable";

export type PVReportStatus = "draft" | "submitted" | "nullified" | "followup";
export type PVCaseReportType = "initial" | "followup" | "nullification";
export type PVExtractionSource = "llm" | "rules";

export interface PVPatient {
  identifier?: string | null;
  age?: number | null;
  age_group?: string | null;
  sex?: string | null;
  initials?: string | null;
  dob?: string | null;
}

export interface PVDrug {
  name?: string | null;
  batch_number?: string | null;
  dose_text?: string | null;
  route_of_administration?: string | null;
  indication?: string | null;
  action_taken?: PVActionTaken | null;
  therapy_start_date?: string | null;
  therapy_end_date?: string | null;
}

export interface MedDRACoding {
  pt_code: string;
  pt_name: string;
  version?: string | null;
  source?: "llm_suggestion" | "user_confirmed" | "cache" | null;
  confirmed_at?: string | null;
}

export interface PVFollowUp {
  report_id: string;
  date: string;
  description?: string | null;
}

export interface PVExpectedReaction {
  pt_code: string;
  pt_name: string;
  severity?: PVSeverity | null;
  causality?: PVCausality | null;
  notes?: string | null;
}

export interface ADRReport {
  report_id: string;
  worldwide_unique_id?: string | null;
  case_version: number;
  case_report_type: PVCaseReportType;
  organization?: string | null;
  product_name: string;
  drug?: PVDrug | null;
  reaction_pt_code?: string | null;
  reaction_pt_name?: string | null;
  reaction_meddra_term?: string | null;
  reaction_description?: string | null;
  reaction_start_date?: string | null;
  seriousness_criteria: string[];
  is_serious: boolean;
  severity?: PVSeverity | null;
  causality?: PVCausality | null;
  outcome?: PVOutcome | null;
  patient?: PVPatient | null;
  reporter_name?: string | null;
  reporter_email?: string | null;
  reporter_phone?: string | null;
  reporter_organisation?: string | null;
  reporter_qualification?: string | null;
  reporter_country?: string | null;
  expectedness?: "expected" | "unexpected" | "not_assessable" | null;
  expectedness_rationale?: string | null;
  expectedness_assessed_by?: string | null;
  expectedness_assessed_at?: string | null;
  expectedness_rsi_version?: string | null;
  is_susar: boolean;
  meddra?: MedDRACoding | null;
  meddra_version?: string | null;
  follow_ups: PVFollowUp[];
  status: PVReportStatus;
  first_received_date?: string | null;
  nullification_reason?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface PVMinimumCriteriaCheck {
  patient: boolean;
  reporter: boolean;
  product: boolean;
  reaction: boolean;
  missing: string[];
  description: string;
}

export interface PVReportDraft {
  product_name?: string | null;
  patient?: PVPatient | null;
  drug?: PVDrug | null;
  reaction_meddra_term?: string | null;
  reaction_description?: string | null;
  reaction_start_date?: string | null;
  seriousness_criteria?: string[] | null;
  is_serious?: boolean | null;
  severity?: PVSeverity | null;
  causality?: PVCausality | null;
  outcome?: PVOutcome | null;
  reporter_name?: string | null;
  reporter_email?: string | null;
  reporter_phone?: string | null;
  reporter_organisation?: string | null;
  reporter_qualification?: string | null;
  reporter_country?: string | null;
  first_received_date?: string | null;
  worldwide_unique_id?: string | null;
  organization?: string | null;
  extraction_source: PVExtractionSource;
}

export interface GeneratedDoc {
  section_path: string;
  stem: string;
  filename: string;
  title: string;
  module: string;
  status: string;
  updated_at: string;
  feedback_count: number;
}
