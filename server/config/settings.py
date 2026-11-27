"""
Centralized Application Settings using Pydantic Settings (with fallback).
"""

import os
from functools import lru_cache
from typing import List
from dotenv import load_dotenv
from server.config.constants import Environment

# Load environment variables from .env if present
load_dotenv()
load_dotenv("../.env")

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=(".env", "../.env"),
            env_file_encoding="utf-8",
            extra="ignore",
        )

        # Server Info
        PROJECT_NAME: str = "Export Customs Documentation Compliance Checker"
        API_V1_STR: str = "/api/v1"
        SERVER_HOST: str = "0.0.0.0"
        SERVER_PORT: int = 8000
        SERVER_ENV: Environment = Environment.DEVELOPMENT
        SERVER_LOG_LEVEL: str = "INFO"

        # CORS
        CORS_ORIGINS: List[str] = [
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
        ]

        # Access Control / Single-User Workflow Mode
        SINGLE_USER_MODE: bool = False

        # AI (Gemini)
        GEMINI_API_KEY: str = "your_gemini_api_key_here"
        GEMINI_MODEL: str = "gemini-2.5-flash"
        GEMINI_API_VERSION: str = "v1beta"
        GEMINI_TIMEOUT_SECONDS: float = 30.0
        GEMINI_MAX_RETRIES: int = 3
        GEMINI_RETRY_BASE_DELAY_SECONDS: float = 1.0
        GEMINI_ENABLE_PYMUPDF_FALLBACK: bool = True

        # Database & Storage (Supabase)
        SUPABASE_URL: str = "your_supabase_project_url_here"
        SUPABASE_KEY: str = "your_supabase_api_key_here"
        SUPABASE_ANON_KEY: str = ""
        SUPABASE_JWT_SECRET: str = ""
        SUPABASE_DB_URL: str = ""
        SUPABASE_ACCESS_TOKEN: str = ""
        SUPABASE_TABLE_NAME: str = "customs_documents"
        SUPABASE_STORAGE_BUCKET: str = "customs-documents"
        SIGNED_URL_TTL_SECONDS: int = 300

        # Vector DB (Pinecone)
        PINECONE_API_KEY: str = "your_pinecone_api_key_here"
        PINECONE_INDEX_NAME: str = "export-customs-rules"
        PINECONE_NAMESPACE: str = "indian-export-regulations-v1"
        PINECONE_ENVIRONMENT: str = "us-east-1"

        # Batch Ingestion Limits
        MAX_BATCH_FILES: int = 5
        MAX_FILE_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB

        # Real-Time Government Rule Sync & Scheduler
        RULE_SYNC_ENABLED: bool = True
        RULE_SYNC_INTERVAL_HOURS: float = 24.0
        RULE_SYNC_INITIAL_DELAY_SECONDS: float = 30.0
        RULE_SYNC_TIMEOUT_SECONDS: float = 20.0
        RULE_SYNC_MAX_ITEMS_PER_SOURCE: int = 25
        RULE_SYNC_FETCH_PDF_TEXT: bool = True
        CBIC_CA_BUNDLE_PATH: str | None = None


except ImportError:
    from pydantic import BaseModel, Field

    class Settings(BaseModel):
        PROJECT_NAME: str = Field(default_factory=lambda: os.getenv("PROJECT_NAME", "Export Customs Documentation Compliance Checker"))
        API_V1_STR: str = Field(default_factory=lambda: os.getenv("API_V1_STR", "/api/v1"))
        SERVER_HOST: str = Field(default_factory=lambda: os.getenv("SERVER_HOST", "0.0.0.0"))
        SERVER_PORT: int = Field(default_factory=lambda: int(os.getenv("SERVER_PORT", "8000")))
        SERVER_ENV: Environment = Field(default_factory=lambda: Environment(os.getenv("SERVER_ENV", "development")))
        SERVER_LOG_LEVEL: str = Field(default_factory=lambda: os.getenv("SERVER_LOG_LEVEL", "INFO"))

        CORS_ORIGINS: List[str] = [
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
        ]

        GEMINI_API_KEY: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", "your_gemini_api_key_here"))
        SINGLE_USER_MODE: bool = Field(
            default_factory=lambda: os.getenv("SINGLE_USER_MODE", "false").lower() in ("1", "true", "yes")
        )
        GEMINI_MODEL: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
        GEMINI_API_VERSION: str = Field(default_factory=lambda: os.getenv("GEMINI_API_VERSION", "v1beta"))
        GEMINI_TIMEOUT_SECONDS: float = Field(default_factory=lambda: float(os.getenv("GEMINI_TIMEOUT_SECONDS", "30.0")))
        GEMINI_MAX_RETRIES: int = Field(default_factory=lambda: int(os.getenv("GEMINI_MAX_RETRIES", "3")))
        GEMINI_RETRY_BASE_DELAY_SECONDS: float = Field(default_factory=lambda: float(os.getenv("GEMINI_RETRY_BASE_DELAY_SECONDS", "1.0")))
        GEMINI_ENABLE_PYMUPDF_FALLBACK: bool = Field(default_factory=lambda: os.getenv("GEMINI_ENABLE_PYMUPDF_FALLBACK", "true").lower() in ("1", "true", "yes"))

        SUPABASE_URL: str = Field(default_factory=lambda: os.getenv("SUPABASE_URL", "your_supabase_project_url_here"))
        SUPABASE_KEY: str = Field(default_factory=lambda: os.getenv("SUPABASE_KEY", "your_supabase_api_key_here"))
        SUPABASE_ANON_KEY: str = Field(default_factory=lambda: os.getenv("SUPABASE_ANON_KEY", ""))
        SUPABASE_JWT_SECRET: str = Field(default_factory=lambda: os.getenv("SUPABASE_JWT_SECRET", ""))
        SUPABASE_DB_URL: str = Field(default_factory=lambda: os.getenv("SUPABASE_DB_URL", ""))
        SUPABASE_ACCESS_TOKEN: str = Field(default_factory=lambda: os.getenv("SUPABASE_ACCESS_TOKEN", ""))
        SUPABASE_TABLE_NAME: str = Field(default_factory=lambda: os.getenv("SUPABASE_TABLE_NAME", "customs_documents"))
        SUPABASE_STORAGE_BUCKET: str = Field(default_factory=lambda: os.getenv("SUPABASE_STORAGE_BUCKET", "customs-documents"))
        SIGNED_URL_TTL_SECONDS: int = Field(default_factory=lambda: int(os.getenv("SIGNED_URL_TTL_SECONDS", "300")))

        PINECONE_API_KEY: str = Field(default_factory=lambda: os.getenv("PINECONE_API_KEY", "your_pinecone_api_key_here"))
        PINECONE_INDEX_NAME: str = Field(default_factory=lambda: os.getenv("PINECONE_INDEX_NAME", "export-customs-rules"))
        PINECONE_NAMESPACE: str = Field(default_factory=lambda: os.getenv("PINECONE_NAMESPACE", "indian-export-regulations-v1"))
        PINECONE_ENVIRONMENT: str = Field(default_factory=lambda: os.getenv("PINECONE_ENVIRONMENT", "us-east-1"))

        MAX_BATCH_FILES: int = Field(default_factory=lambda: int(os.getenv("MAX_BATCH_FILES", "5")))
        MAX_FILE_SIZE_BYTES: int = Field(default_factory=lambda: int(os.getenv("MAX_FILE_SIZE_BYTES", str(25 * 1024 * 1024))))

        RULE_SYNC_ENABLED: bool = Field(default_factory=lambda: os.getenv("RULE_SYNC_ENABLED", "true").lower() in ("1", "true", "yes"))
        RULE_SYNC_INTERVAL_HOURS: float = Field(default_factory=lambda: float(os.getenv("RULE_SYNC_INTERVAL_HOURS", "24.0")))
        RULE_SYNC_INITIAL_DELAY_SECONDS: float = Field(default_factory=lambda: float(os.getenv("RULE_SYNC_INITIAL_DELAY_SECONDS", "30.0")))
        RULE_SYNC_TIMEOUT_SECONDS: float = Field(default_factory=lambda: float(os.getenv("RULE_SYNC_TIMEOUT_SECONDS", "20.0")))
        RULE_SYNC_MAX_ITEMS_PER_SOURCE: int = Field(default_factory=lambda: int(os.getenv("RULE_SYNC_MAX_ITEMS_PER_SOURCE", "25")))
        RULE_SYNC_FETCH_PDF_TEXT: bool = Field(default_factory=lambda: os.getenv("RULE_SYNC_FETCH_PDF_TEXT", "true").lower() in ("1", "true", "yes"))
        CBIC_CA_BUNDLE_PATH: str | None = Field(default_factory=lambda: os.getenv("CBIC_CA_BUNDLE_PATH") or None)




@lru_cache()
def get_settings() -> Settings:
    return Settings()
