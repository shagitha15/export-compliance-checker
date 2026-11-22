"""
Health Check Schemas.
"""

from pydantic import BaseModel, Field


class SystemComponentStatus(BaseModel):
    database: bool = Field(..., description="Supabase PostgreSQL status")
    vector_db: bool = Field(..., description="Pinecone Vector DB status")
    ai_service: bool = Field(..., description="Google Gemini API status")


class HealthResponse(BaseModel):
    status: str = Field(..., description="'healthy', 'degraded', or 'unhealthy'")
    version: str = Field(..., description="Server version")
    environment: str = Field(..., description="Running environment")
    timestamp: str = Field(..., description="UTC ISO-8601 timestamp")
    components: SystemComponentStatus
