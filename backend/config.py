from functools import lru_cache
from typing import Any

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field("demo", validation_alias=AliasChoices("APP_ENV", "ENVIRONMENT"))
    local_only: bool = Field(True, validation_alias=AliasChoices("LOCAL_ONLY", "USE_LOCAL_STACK_ONLY"))
    database_url: str = Field("sqlite:///./resq_ai.db", validation_alias=AliasChoices("DATABASE_URL", "POSTGRES_URL"))
    llm_provider: str = "ollama"
    llm_model: str = "llama3.2:1b"
    llm_api_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"
    speech_provider: str = "faster-whisper"
    whisper_model: str = "small"
    tts_provider: str = "piper"
    piper_bin: str = "piper"
    piper_models_dir: str = "./models/piper"
    piper_model_en: str = ""
    piper_model_hi: str = ""
    piper_model_gu: str = ""
    vision_provider: str = "yolo"
    yolo_model: str = "yolo11n.pt"
    routing_provider: str = "osrm"
    osrm_url: str = "https://router.project-osrm.org"
    upload_dir: str = "./uploads"
    max_file_size_mb: int = Field(10, validation_alias=AliasChoices("MAX_FILE_SIZE_MB", "MAX_UPLOAD_SIZE_MB"))
    allowed_extensions: str = ".png,.jpg,.jpeg,.mp4,.wav,.mp3,.pdf"
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    frontend_url: str = Field("http://localhost:3000", validation_alias="FRONTEND_URL")
    rate_limit_per_minute: int = Field(120, validation_alias="RATE_LIMIT_PER_MINUTE")
    api_key: str = ""
    require_auth: bool = Field(False, validation_alias=AliasChoices("REQUIRE_AUTH", "AUTH_REQUIRED"))
    auth_secret: str = Field("change-this-development-secret", validation_alias=AliasChoices("AUTH_SECRET", "JWT_SECRET"))
    access_token_minutes: int = Field(60, validation_alias=AliasChoices("ACCESS_TOKEN_MINUTES", "JWT_ACCESS_TOKEN_EXPIRE_MINUTES"))
    notification_webhook_url: str = Field("", validation_alias=AliasChoices("NOTIFICATION_WEBHOOK_URL", "LOCAL_WEBHOOK_URL"))
    smtp_host: str = Field("", validation_alias=AliasChoices("SMTP_HOST", "LOCAL_SMTP_HOST"))
    smtp_port: int = Field(25, validation_alias=AliasChoices("SMTP_PORT", "LOCAL_SMTP_PORT"))
    smtp_username: str = Field("", validation_alias=AliasChoices("SMTP_USERNAME", "LOCAL_SMTP_USERNAME"))
    smtp_password: str = Field("", validation_alias=AliasChoices("SMTP_PASSWORD", "LOCAL_SMTP_PASSWORD"))
    smtp_from: str = Field("resq-ai@localhost", validation_alias=AliasChoices("SMTP_FROM", "LOCAL_SMTP_FROM"))
    default_roles: str = Field("admin,operator,viewer", validation_alias=AliasChoices("DEFAULT_ROLES", "LOCAL_AUTH_ROLES"))

    @field_validator("database_url", mode="before")
    @classmethod
    def use_sqlite_when_database_url_is_blank(cls, value: str) -> str:
        return value or "sqlite:///./resq_ai.db"

    @field_validator("auth_secret")
    @classmethod
    def reject_default_auth_secret_in_production(cls, value: str, info: Any) -> str:
        if info.data.get("app_env", "demo").lower() in {"production", "prod"} and value == "change-this-development-secret":
            raise ValueError("AUTH_SECRET must be set when APP_ENV is production")
        return value

    @model_validator(mode="after")
    def validate_production_controls(self) -> "Settings":
        if self.app_env.lower() in {"production", "prod"}:
            if not self.require_auth:
                raise ValueError("REQUIRE_AUTH must be true when APP_ENV is production")
            if self.database_url.startswith("sqlite"):
                raise ValueError("DATABASE_URL must use PostgreSQL when APP_ENV is production")
        return self

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
