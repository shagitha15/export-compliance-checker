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
            "http://localhost:3000",
            "http://127.0.0.1:5173",
        ]

        # AI (Gemini)
        GEMINI_API_KEY: str = "your_gemini_api_key_here"
        GEMINI_MODEL: str = "gemini-2.5-flash"
        GEMINI_API_VERSION: str = "v1beta"

        # Database (Supabase)
        SUPABASE_URL: str = "your_supabase_project_url_here"
        SUPABASE_KEY: str = "your_supabase_api_key_here"
        SUPABASE_TABLE_NAME: str = "customs_documents"

        # Vector DB (Pinecone)
        PINECONE_API_KEY: str = "your_pinecone_api_key_here"
        PINECONE_INDEX_NAME: str = "export-customs-rules"
        PINECONE_NAMESPACE: str = "indian-export-regulations-v1"
        PINECONE_ENVIRONMENT: str = "us-east-1"

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
            "http://localhost:3000",
            "http://127.0.0.1:5173",
        ]

        GEMINI_API_KEY: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", "your_gemini_api_key_here"))
        GEMINI_MODEL: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
        GEMINI_API_VERSION: str = Field(default_factory=lambda: os.getenv("GEMINI_API_VERSION", "v1beta"))

        SUPABASE_URL: str = Field(default_factory=lambda: os.getenv("SUPABASE_URL", "your_supabase_project_url_here"))
        SUPABASE_KEY: str = Field(default_factory=lambda: os.getenv("SUPABASE_KEY", "your_supabase_api_key_here"))
        SUPABASE_TABLE_NAME: str = Field(default_factory=lambda: os.getenv("SUPABASE_TABLE_NAME", "customs_documents"))

        PINECONE_API_KEY: str = Field(default_factory=lambda: os.getenv("PINECONE_API_KEY", "your_pinecone_api_key_here"))
        PINECONE_INDEX_NAME: str = Field(default_factory=lambda: os.getenv("PINECONE_INDEX_NAME", "export-customs-rules"))
        PINECONE_NAMESPACE: str = Field(default_factory=lambda: os.getenv("PINECONE_NAMESPACE", "indian-export-regulations-v1"))
        PINECONE_ENVIRONMENT: str = Field(default_factory=lambda: os.getenv("PINECONE_ENVIRONMENT", "us-east-1"))



@lru_cache()
def get_settings() -> Settings:
    return Settings()
