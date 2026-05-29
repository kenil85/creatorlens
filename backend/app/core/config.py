from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_env: str = "development"
    app_secret_key: str = "dev-secret-change-in-prod"
    cors_origins: str = "http://localhost:3000"

    # Groq (free)
    groq_api_key: str

    # Supabase
    supabase_url: str
    supabase_service_key: str

    # Rate limiting
    rate_limit_per_minute: int = 10

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
