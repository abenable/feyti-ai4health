from pydantic import BaseModel


class AnalysisMetadata(BaseModel):
    filename: str
    content_type: str
    size_bytes: int


class AnalysisResponse(BaseModel):
    summary: str
    metadata: AnalysisMetadata


class Classification(BaseModel):
    section_path: str
    title: str
    module: str
    confidence: float
    justification: str


class ProcessResponse(BaseModel):
    filename: str
    extracted_chars: int
    ocr_used: bool
    classification: Classification
    summary: str = ""
    key_points: list[str] = []
    dossier_folder: str


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


class ChatResponse(BaseModel):
    response: str
