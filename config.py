"""Configuration and environment settings"""

from pydantic_settings import BaseSettings
from typing import Optional, List
from pathlib import Path


class Settings(BaseSettings):
    """Application configuration"""
    
    # LLM Configuration
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None  # Gemini API key
    
    # LLM Provider Priority (comma-separated: anthropic,openai,gemini)
    LLM_PROVIDER_PRIORITY: str = "anthropic,openai,gemini"
    
    # LLM Model Selection
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    OPENAI_MODEL: str = "gpt-4o"
    GEMINI_MODEL_ID: Optional[str] = None  # Primary Gemini model (e.g., "gemini-1.5-pro")
    GEMINI_FALLBACK_MODEL_ID: Optional[str] = None  # Fallback Gemini model (e.g., "gemini-2.5-flash")
    
    # LLM Settings
    LLM_MAX_TOKENS: int = 4096
    LLM_MAX_RETRIES: int = 3
    LLM_RETRY_DELAY: float = 2.0  # seconds
    LLM_TIMEOUT: float = 60.0  # seconds
    
    # Database
    DATABASE_URL: Optional[str] = None
    
    # Supabase
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    
    # Output
    OUTPUT_DIR: str = "./output"
    
    # Processing
    MAX_PREVIEW_ROWS: int = 50
    CONFIDENCE_THRESHOLD: float = 0.7
    VALIDATION_FAILURE_THRESHOLD: float = 0.1  # 10%
    
    # Insights
    MIN_VARIANCE_FOR_INSIGHT: float = 0.1  # 10%
    MAX_INSIGHTS_PER_ANALYSIS: int = 10
    
    # Authentication
    JWT_SECRET_KEY: Optional[str] = None  # Auto-generated if not set
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRY_HOURS: int = 1
    JWT_REFRESH_TOKEN_EXPIRY_DAYS: int = 30
    
    # Archaeology
    ARCHAEOLOGY_MAX_PREVIEW_ROWS: int = 50
    FUZZY_MATCH_THRESHOLD: int = 80

    # Excel-to-web-app generator (Stages 8-12)
    EXCEL_APP_GENERATION_ENABLED: bool = False

    # ETL-only parsing behavior
    ETL_INPUTS_ONLY: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env (like AWS_* variables)
    
    def get_llm_provider_priority(self) -> List[str]:
        """Get LLM provider priority list"""
        return [p.strip() for p in self.LLM_PROVIDER_PRIORITY.split(",")]
    
    def get_output_path(self, subdir: str = "") -> Path:
        """Get output directory path"""
        path = Path(self.OUTPUT_DIR) / subdir
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()

