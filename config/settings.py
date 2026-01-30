from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    openai_api_key: Optional[str] = None
    model_name: str = "Qwen/QwQ-32B"
    temperature: float = 0.7
    max_tokens: int = 2000
    confidence_threshold: float = 0.70
    context_window_size: int = 4000
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    spacy_model: str = "en_core_web_lg"
    intent_model_path: str = "models/intent_classifier"
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()