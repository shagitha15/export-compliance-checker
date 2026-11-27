"""
Fraud & Fake Document Detection API Routes (v1).
"""

from fastapi import APIRouter, Depends, File, UploadFile, status

from server.auth.dependencies import require_workflow_context
from server.auth.models import OrganizationContext, WRITER_ROLES
from server.controllers.fraud_controller import FraudController
from server.schemas.fraud import (
    FraudAnalysisReport,
    InspectDocumentsRequest,
    PdfForensicsResult,
)

router = APIRouter(prefix="/fraud", tags=["Fraud & Fake Document Detection"])


@router.post(
    "/inspect",
    response_model=FraudAnalysisReport,
    status_code=status.HTTP_200_OK,
    summary="Inspect Extracted Document Dataset for Fraud & Forgery",
    description=(
        "Executes multi-layer forensic analysis on shipment documents: "
        "validating Indian GSTIN Mod-36 checksums, DGFT IEC syntax, "
        "line-item arithmetic integrity, Net <= Gross weight physical laws, "
        "and cross-document temporal ordering paradoxes."
    ),
)
def inspect_extracted_documents(
    payload: InspectDocumentsRequest,
    org_context: OrganizationContext | None = Depends(require_workflow_context()),
) -> FraudAnalysisReport:
    """Evaluates extracted document data against forensic authenticity rules."""
    return FraudController.inspect_documents(payload=payload)


@router.post(
    "/inspect-file",
    response_model=PdfForensicsResult,
    status_code=status.HTTP_200_OK,
    summary="Inspect Raw PDF Binary File for Digital Tampering",
    description=(
        "Performs deep digital forensics on a binary PDF: auditing producer/creator metadata "
        "against consumer editing tools (Photoshop, Canva, iLovePDF, Sejda), comparing creation vs "
        "modification timestamps, and detecting font-splicing anomalies."
    ),
)
async def inspect_pdf_file(
    file: UploadFile = File(..., description="Target PDF file for forensic analysis"),
    org_context: OrganizationContext | None = Depends(require_workflow_context(WRITER_ROLES)),
) -> PdfForensicsResult:
    """Analyzes a binary PDF file for digital tampering and metadata alteration."""
    return await FraudController.inspect_pdf_file(file=file)
