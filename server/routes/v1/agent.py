"""
LangGraph AI Customs Compliance Agent API Routes (v1).
"""

from fastapi import APIRouter, Depends, status

from server.auth.dependencies import require_workflow_context
from server.auth.models import OrganizationContext, WRITER_ROLES
from server.controllers.agent_controller import AgentController
from server.schemas.agent import AgentAnalysisResponse, AgentAnalyzeRequest

router = APIRouter(prefix="/agent", tags=["AI Compliance Agent"])


@router.post(
    "/analyze",
    response_model=AgentAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute LangGraph Autonomous Export Compliance Audit",
    description=(
        "Executes a stateful 10-node LangGraph workflow coordinating document completeness checks, "
        "16 cross-document reconciliation rules, Indian statutory compliance verification (DGFT, CBIC, RBI), "
        "multi-layer fraud/authenticity forensics, and official A4 PDF certificate generation. "
        "Strictly enforces non-overridable rejection on critical fraud anomalies."
    ),
)
def analyze_export_compliance(
    payload: AgentAnalyzeRequest,
    org_context: OrganizationContext | None = Depends(require_workflow_context(WRITER_ROLES)),
) -> AgentAnalysisResponse:
    """Invokes the LangGraph compliance agent workflow to audit an export consignment."""
    return AgentController.analyze_shipment(payload=payload)
