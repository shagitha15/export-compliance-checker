"""
API Version 1 Router Aggregator.
Registers all versioned sub-routers for auth, organizations, audits, health, documents, fraud, and compliance.
"""

from fastapi import APIRouter
from server.routes.v1.agent import router as agent_router
from server.routes.v1.audits import router as audits_router
from server.routes.v1.auth import router as auth_router
from server.routes.v1.compliance import router as compliance_router
from server.routes.v1.documents import router as documents_router
from server.routes.v1.fraud import router as fraud_router
from server.routes.v1.health import router as health_router
from server.routes.v1.orgs import router as orgs_router
from server.routes.v1.rules import router as rules_router

api_v1_router = APIRouter(prefix="/api/v1")

# Mount versioned sub-routers
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(orgs_router)
api_v1_router.include_router(audits_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(compliance_router)
api_v1_router.include_router(fraud_router)
api_v1_router.include_router(agent_router)
api_v1_router.include_router(rules_router)

__all__ = ["api_v1_router"]
