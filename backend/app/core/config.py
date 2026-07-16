from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Feyti"
    API_V1_STR: str = "/api/v1"
    # LLM provider for text reasoning (classification). "gemini" or "deepseek".
    # OCR always uses Gemini (DeepSeek has no vision).
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    # OCR provider for scanned PDFs: "cloudflare" (Moondream) or "gemini".
    OCR_PROVIDER: str = "cloudflare"
    CLOUDFLARE_ACCOUNT_ID: str = ""
    CLOUDFLARE_API_TOKEN: str = ""
    CLOUDFLARE_OCR_MODEL: str = "@cf/moondream/moondream3.1-9B-A2B"
    DOSSIER_ROOT: str = "./dossier"
    # Hosted Aicyclinder model (ngrok public URL from the hosting notebook).
    AICYCLINDER_API_URL: str = "https://congenial-premises-chill.ngrok-free.dev"
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
