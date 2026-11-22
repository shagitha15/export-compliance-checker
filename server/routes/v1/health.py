"""
Health Check Route.
"""

from fastapi import APIRouter, status
from server.controllers.health_controller import HealthController
from server.schemas.common import ApiResponse
from server.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["System Health"])


@router.get(
    "",
    response_model=ApiResponse[HealthResponse],
    status_code=status.HTTP_200_OK,
    summary="System Health & Component Status",
)
async def check_health() -> ApiResponse[HealthResponse]:
    return await HealthController.get_health_status()
