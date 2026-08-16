// Shared response/request types for the Feyti API. Single source of truth —
// previously duplicated across app/page.tsx, app/review/page.tsx, app/chat/page.tsx.

export type ReviewStatusValue = "draft" | "edited" | "approved";

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
