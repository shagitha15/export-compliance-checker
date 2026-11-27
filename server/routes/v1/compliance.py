"""
Compliance Validation & Statutory Regulatory Audit API Routes (v1).
"""

from fastapi import APIRouter, Depends, Response, status

from server.auth.dependencies import require_workflow_context
from server.auth.models import OrganizationContext
from server.controllers.compliance_controller import ComplianceController
from server.schemas.compliance import ComplianceAuditResponse, GovernmentComplianceReport
from server.schemas.report import GeneratePdfReportRequest
from server.schemas.validation import (
    CrossDocumentValidationResponse,
    ValidateStoredFilesPayload,
    ValidationDirectPayload,
)

router = APIRouter(prefix="/compliance", tags=["Compliance & Verification"])


@router.post(
    "/validate",
    response_model=CrossDocumentValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Cross-Document Compliance Validation (Direct JSON)",
    description=(
        "Executes two-stage validation (document-specific integrity and cross-document reconciliation) "
        "on provided extracted JSON document data. Returns PASS, FAIL, and NOT APPLICABLE check results."
    ),
)
async def validate_extracted_documents(
    payload: ValidationDirectPayload,
    org_context: OrganizationContext | None = Depends(require_workflow_context()),
) -> CrossDocumentValidationResponse:
    """
    Validates a set of extracted document JSONs across 16 reconciliation rules.
    """
    return await ComplianceController.validate_documents(payload=payload)


@router.post(
    "/validate-stored",
    response_model=CrossDocumentValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Cross-Document Validation for Stored Documents",
    description=(
        "Loads extracted document JSONs from Supabase (or extracted_data/ fallback) "
        "and executes cross-document reconciliation."
    ),
)
async def validate_stored_documents(
    payload: ValidateStoredFilesPayload,
    org_context: OrganizationContext | None = Depends(require_workflow_context()),
) -> CrossDocumentValidationResponse:
    """
    Loads saved documents from database or disk cache and runs cross-document reconciliation.
    """
    return await ComplianceController.validate_stored_documents(
        payload=payload,
        org_context=org_context,
    )


@router.post(
    "/verify-rules",
    response_model=GovernmentComplianceReport,
    status_code=status.HTTP_200_OK,
    summary="Verify Shipment Against Official Indian Government Export Regulations",
    description=(
        "Retrieves statutory export rules semantically from the Pinecone vector index "
        "(DGFT FTP 2023, CBIC Customs Act, RBI FEMA, SCOMET) and audits shipment documents "
        "against government mandates, providing official citations and source URLs."
    ),
)
async def verify_statutory_rules(
    payload: ValidationDirectPayload,
    org_context: OrganizationContext | None = Depends(require_workflow_context()),
) -> GovernmentComplianceReport:
    """
    Audits shipment data against Indian statutory export policies retrieved via vector search.
    """
    return await ComplianceController.verify_statutory_rules(payload=payload)


@router.post(
    "/verify-government-rules",
    response_model=GovernmentComplianceReport,
    status_code=status.HTTP_200_OK,
    summary="Verify Shipment Against Indian Government Regulations (Compatibility Alias)",
    description="Backward-compatible route alias for statutory export rules verification.",
    include_in_schema=False,
)
async def verify_government_rules_alias(
    payload: ValidationDirectPayload,
    org_context: OrganizationContext | None = Depends(require_workflow_context()),
) -> GovernmentComplianceReport:
    """
    Compatibility alias for /verify-rules.
    """
    return await ComplianceController.verify_statutory_rules(payload=payload)


@router.post(
    "/audit",
    response_model=ComplianceAuditResponse,
    status_code=status.HTTP_200_OK,
    summary="Unified Shipment Compliance & Statutory Audit",
    description=(
        "Executes complete end-to-end compliance verification in a single invocation: "
        "both two-stage cross-document reconciliation and statutory Indian government rule checking."
    ),
)
async def audit_full_shipment(
    payload: ValidationDirectPayload,
    org_context: OrganizationContext | None = Depends(require_workflow_context()),
) -> ComplianceAuditResponse:
    """
    Performs unified cross-document reconciliation and statutory regulatory verification.
    """
    return await ComplianceController.audit_full_shipment(payload=payload)


@router.post(
    "/report/pdf",
    status_code=status.HTTP_200_OK,
    summary="Generate Official Customs Compliance Certificate (PDF)",
    description=(
        "Renders a publication-quality multi-page A4 PDF Compliance Audit Certificate "
        "from live validation results, complete with executive scorecard, document roster, "
        "16-rule reconciliation matrix, field discrepancies, and Indian statutory findings."
    ),
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Binary PDF Compliance Certificate attachment file.",
        }
    },
)
async def generate_pdf_compliance_report(
    payload: GeneratePdfReportRequest,
    org_context: OrganizationContext | None = Depends(require_workflow_context()),
) -> Response:
    """
    Generates and returns the official binary PDF compliance audit certificate.
    """
    pdf_bytes = ComplianceController.generate_pdf_report(payload=payload, org_context=org_context)
    audit_id = (
        payload.batch_id
        or (payload.cross_document_validation.audit_id if payload.cross_document_validation else "batch_report")
    )
    safe_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in audit_id)
    filename = f"compliance_report_{safe_id}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
