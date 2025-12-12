from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    #app settings
    APP_NAME: str = "Whatsapp Voice AI"
    ENV: str = "production"
    DEBUG: bool = False 
    LOG_LEVEL: str = "INFO"

    #fastapi
    API_VERSION: str = "v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    #mongodb settings
    MONGODB_URI: str = ""
    MONGODB_DB_NAME: str = "healthcare_ai"
    MONGODB_COLLECTION: str = "doctors"
    MONGODB_VECTOR_COLLECTION: str = "treatment_protocols"

    #redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    CONTEXT_TTL: int = 1800

    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    GCP_PROJECT_ID: str
    GCP_STT_LANGUAGE: str = "ur-PK"
    GCP_TTS_LANGUAGE: str = "ur-PK"
    GCP_TTS_VOICE_NAME: str = "ur-PK-Standard-A"

    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-1.5-flash"

    WABA_API_URL: str
    WABA_PHONE_NUMBER_ID: str
    WABA_ACCESS_TOKEN: str
    WABA_VERIFY_TOKEN: str

    MAX_MESSAGES_PER_USER: int = 10
    RATE_LIMIT_WINDOW: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True
    
@lru_cache
def get_settings() -> Settings:
    return Settings()