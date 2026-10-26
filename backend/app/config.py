from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ENV_FILE,
        env_prefix="CMSQI_",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg://cms_quality:cms_quality_dev@localhost:5432/cms_quality_demo"
    )
    default_from_year: int = 2025
    default_to_year: int = 2026
    admin_username: str | None = None
    admin_password_hash: str | None = None
    admin_session_secret: str | None = None
    admin_session_secure: bool = False
    admin_session_ttl_seconds: int = 8 * 60 * 60
    source_fetch_timeout_seconds: float = 30.0
    source_fetch_max_bytes: int = 25 * 1024 * 1024
    source_fetch_max_redirects: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
