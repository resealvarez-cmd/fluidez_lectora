"""
Configuración central y settings del backend
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite+aiosqlite:///./fluidez_lectora.db"
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    ASR_ENGINE: str = "openai" # "openai", "gemini", or "mock"
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    AUDIO_STORAGE_BUCKET: str = "lecturas-audio"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALLOWED_ORIGINS: str = "*"

    # Thresholds de análisis
    PAUSA_LARGA_SEGUNDOS: float = 2.5
    VACILACION_SEGUNDOS: float = 1.0

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
