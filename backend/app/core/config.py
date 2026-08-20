from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Feyti"
    API_V1_STR: str = "/api/v1"
    # Text reasoning (classification) always tries Aicyclinder (self-hosted)
    # first, falling back to Kimi then Gemini on error — see llm.py.
    # OCR always uses Gemini (neither fallback offers vision).
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"
    KIMI_API_KEY: str = ""
    KIMI_MODEL: str = "kimi-k3"
    KIMI_BASE_URL: str = "https://api.moonshot.ai/v1"
    # OCR provider for scanned PDFs: "cloudflare" (Moondream) or "gemini".
    OCR_PROVIDER: str = "cloudflare"
    CLOUDFLARE_ACCOUNT_ID: str = ""
    CLOUDFLARE_API_TOKEN: str = ""
    CLOUDFLARE_OCR_MODEL: str = "@cf/moondream/moondream3.1-9B-A2B"
    # Container directory holding one subfolder per dossier.
    DOSSIERS_ROOT: str = "./dossiers"
    # Pre-multi-dossier layout ("./dossier", singular) — migrated into
    # DOSSIERS_ROOT/default on first run if found. Safe to ignore afterwards.
    LEGACY_DOSSIER_ROOT: str = "./dossier"
    # Self-hosted Aicyclinder box (unsloth/Qwen3.8-27B + CTD-classifier LoRA,
    # GPU EC2 instance). /invocations classifies (classification_service);
    # /v1/chat/completions is the LoRA-disabled base model for freeform
    # generation (llm.py's fallback chain, and chat.py).
    FEYTI_CTD_API_URL: str = "http://44.219.130.128:8080"
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()
