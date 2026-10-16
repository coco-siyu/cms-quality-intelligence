from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CMSQI_",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg://cms_quality:cms_quality_dev@localhost:5432/cms_quality_demo"
    )
    default_from_year: int = 2025
    default_to_year: int = 2026


@lru_cache
def get_settings() -> Settings:
    return Settings()
