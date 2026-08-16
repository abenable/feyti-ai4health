from pydantic import BaseModel


class DossierSummary(BaseModel):
    id: str
    name: str
    product_name: str = ""
    created_at: str
    filed: int  # documents filed
    approved: int


class CreateDossierRequest(BaseModel):
    name: str


class Classification(BaseModel):
    section_path: str
    title: str
    module: str
    confidence: float
    justification: str


class ExtractedField(BaseModel):
    label: str
    value: str
    page: int = 0
    confidence: float = 0.0


class ProcessResponse(BaseModel):
    filename: str
    extracted_chars: int
    ocr_used: bool
    classification: Classification
    summary: str = ""
    key_points: list[str] = []
    fields: list[ExtractedField] = []
    dossier_folder: str
    section_path: str = ""  # folder path, so the frontend can deep-link into the workspace
    stem: str = ""


class SourcePage(BaseModel):
    page: int
    text: str
    is_ocr: bool = False


class SourceDoc(BaseModel):
    pages: list[SourcePage]
    had_ocr: bool
    extracted_chars: int
    filename: str


class DossierDocument(BaseModel):
    name: str
    confidence: float
    uploaded_at: str


class DossierSection(BaseModel):
    section_path: str
    title: str
    documents: list[DossierDocument]


class DossierModule(BaseModel):
    module: str
    sections: list[DossierSection]


# NOTE: in the review/generate models below, `section_path` is the dossier
# FOLDER path "<module>/<section> <title>" (as returned by /documents), NOT the
# bare CTD path like "3.2.P.8.3". The bare CTD path lives in meta["section_path"].
class PlanDoc(BaseModel):
    section_path: str  # folder path, for loading the document
    stem: str
    filename: str
    title: str
    status: str  # draft | edited | approved
    updated_at: str


class PlanSection(BaseModel):
    path: str  # bare CTD path, e.g. "3.2.P.8.3"
    title: str
    status: str  # approved | in_review | empty
    documents: list[PlanDoc]


class PlanModule(BaseModel):
    module: str
    sections: list[PlanSection]


class NewSectionRequest(BaseModel):
    ctd_path: str  # bare CTD path, e.g. "3.2.P.8.3"
    augment: bool = False  # True → AI-author a skeleton; False → blank to write


class ReclassifyRequest(BaseModel):
    section_path: str  # current folder path
    stem: str
    ctd_path: str  # new bare CTD path to move the document to


class ReclassifyResponse(BaseModel):
    section_path: str  # new folder path
    stem: str


class NewSectionResponse(BaseModel):
    section_path: str  # folder path, for loading/editing the new document
    stem: str
    markdown: str
    status: str


class ModuleReadiness(BaseModel):
    module: str
    approved: int
    in_review: int
    empty: int
    drafted: int  # approved + in_review (engaged)


class ReadinessReport(BaseModel):
    score: int  # 0..100 — approved / engaged
    verdict_label: str  # ready | nearly | not_ready
    totals: dict  # approved / in_review / empty / engaged / catalogue
    open_gaps: int  # total "⚠️ TO BE PROVIDED" markers across drafts
    modules: list[ModuleReadiness]
    narrative: str  # AI markdown: verdict + blockers + next actions


class ProductContext(BaseModel):
    """Dossier-wide product details, captured before upload to ground the
    classification and generation prompts. All fields optional."""
    product_name: str = ""
    active_ingredient: str = ""
    dosage_form: str = ""
    strength: str = ""
    applicant: str = ""
    market: str = ""  # target region / regulatory authority


class GeneratedDoc(BaseModel):
    section_path: str  # folder path: "<module>/<section> <title>"
    stem: str
    filename: str
    title: str
    module: str
    status: str
    updated_at: str
    feedback_count: int


class ValidationCheck(BaseModel):
    id: str
    level: str  # "error" | "warn"
    message: str
    line: int | None = None


class ValidationReport(BaseModel):
    checks: list[ValidationCheck]
    open_gaps: int
    score: int  # 0..100, deterministic
    narrative: str  # AI markdown: unsupported-claim flags


class ReviewStatus(BaseModel):
    status: str
    updated_at: str
    feedback_history: list[dict]


class DocumentDetail(BaseModel):
    markdown: str
    status: str  # review state string ("draft"|"edited"|"approved")
    meta: dict


class GenerateRequest(BaseModel):
    section_path: str
    stem: str
    augment: bool = False  # expand sparse source into a complete section w/ gap markers


class EditRequest(BaseModel):
    section_path: str
    stem: str
    markdown: str


class FeedbackRequest(BaseModel):
    section_path: str
    stem: str
    feedback: str


class GenerateResponse(BaseModel):
    markdown: str
    status: str  # review state string ("draft"|"edited"|"approved")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    max_new_tokens: int = 512
    temperature: float = 0.0
    # "aicyclinder" = hosted fine-tuned model; "cloud" = DeepSeek (kept internal).
    provider: str = "aicyclinder"
    # Optional: when chat is opened from a document workspace, grounds the
    # assistant in that document's draft in addition to dossier-wide context.
    section_path: str | None = None
    stem: str | None = None


class ChatResponse(BaseModel):
    response: str
