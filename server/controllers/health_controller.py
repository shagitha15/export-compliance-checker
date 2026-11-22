"""
Health Check Controller.
"""

from datetime import datetime, timezone
import os
from server.config.settings import get_settings
from server.schemas.common import ApiResponse
from server.schemas.health import HealthResponse, SystemComponentStatus


class HealthController:
    @staticmethod
    async def get_health_status() -> ApiResponse[HealthResponse]:
        settings = get_settings()

        # Check credentials presence for components
        db_ready = bool(
            settings.SUPABASE_URL
            and settings.SUPABASE_URL != "your_supabase_project_url_here"
        )
        vector_ready = bool(
            settings.PINECONE_API_KEY
            and settings.PINECONE_API_KEY != "your_pinecone_api_key_here"
        )
        ai_ready = bool(
            settings.GEMINI_API_KEY
            and settings.GEMINI_API_KEY != "your_gemini_api_key_here"
        )

        overall_status = "healthy" if (db_ready and ai_ready) else "degraded"

        health_data = HealthResponse(
            status=overall_status,
            version="1.0.0",
            environment=settings.SERVER_ENV.value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            components=SystemComponentStatus(
                database=db_ready,
                vector_db=vector_ready,
                ai_service=ai_ready,
            ),
        )

        return ApiResponse(
            success=True,
            message="Export Customs Compliance Checker API is running normally.",
            data=health_data,
        )
