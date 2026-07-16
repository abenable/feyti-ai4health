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
