from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # App Settings
    app_name: str = Field(default="AI CV Evaluator", alias="APP_NAME")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    
    # Database
    database_url: str = Field(
        default="sqlite:///./cv_evaluator.db",
        alias="DATABASE_URL"
    )
    
    # Redis & Celery
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        alias="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0",
        alias="CELERY_RESULT_BACKEND"
    )
    
    # LLM API Keys
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY")
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    
    # LLM Configuration
    llm_provider: str = Field(default="openrouter", alias="LLM_PROVIDER")
    llm_model: str = Field(default="anthropic/claude-3-haiku", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.3, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=2000, alias="LLM_MAX_TOKENS")
    
    # Vector Database
    chroma_persist_directory: str = Field(
        default="./chroma_db",
        alias="CHROMA_PERSIST_DIRECTORY"
    )
    chroma_collection_name: str = Field(
        default="cv_evaluator_docs",
        alias="CHROMA_COLLECTION_NAME"
    )
    
    # File Upload
    upload_dir: str = Field(default="./data/uploads", alias="UPLOAD_DIR")
    max_file_size: int = Field(default=10485760, alias="MAX_FILE_SIZE")  # 10MB
    allowed_extensions: str = Field(default="pdf", alias="ALLOWED_EXTENSIONS")
    
    # Evaluation Settings
    retry_max_attempts: int = Field(default=3, alias="RETRY_MAX_ATTEMPTS")
    retry_backoff_factor: int = Field(default=2, alias="RETRY_BACKOFF_FACTOR")
    evaluation_timeout: int = Field(default=300, alias="EVALUATION_TIMEOUT")
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = Field(default="./logs/app.log", alias="LOG_FILE")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"
    
    def get_llm_api_key(self) -> str:
        """Get the API key for the configured LLM provider"""
        provider_key_map = {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "openrouter": self.openrouter_api_key,
            "gemini": self.google_api_key,
        }
        
        api_key = provider_key_map.get(self.llm_provider.lower())
        if not api_key:
            raise ValueError(
                f"API key not found for provider: {self.llm_provider}. "
                f"Please set the appropriate environment variable."
            )
        return api_key
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.upload_dir,
            self.chroma_persist_directory,
            os.path.dirname(self.log_file),
        ]
        for directory in directories:
            if directory:
                os.makedirs(directory, exist_ok=True)


# Global settings instance
settings = Settings()
settings.ensure_directories()