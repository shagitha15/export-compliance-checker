from server.routes.v1.router import api_v1_router
from server.routes.v1.health import router as health_router
from server.routes.v1.documents import router as documents_router
from server.routes.v1.compliance import router as compliance_router

__all__ = [
    "api_v1_router",
    "health_router",
    "documents_router",
    "compliance_router",
]
