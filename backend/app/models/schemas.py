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


class GeneratedDoc(BaseModel):
    section_path: str
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
    status: ReviewStatus
    meta: dict


class GenerateRequest(BaseModel):
    section_path: str
    stem: str


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
    status: ReviewStatus


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
