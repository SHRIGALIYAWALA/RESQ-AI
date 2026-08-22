from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "demo"
    database_url: str = "sqlite:///./resq_ai.db"
    llm_provider: str = "simulated"
    llm_model: str = "simulated-demo"
    llm_api_key: str = ""
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 10
    allowed_extensions: str = ".png,.jpg,.jpeg,.mp4,.wav,.mp3,.pdf"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
