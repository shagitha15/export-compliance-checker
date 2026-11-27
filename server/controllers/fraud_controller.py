"""
Controller for Fake Document and Tamper Detection Operations.
"""

from __future__ import annotations

from typing import Any
from fastapi import HTTPException, UploadFile, status

from server.forensics.engine import FraudDetectionEngine
from server.logging.logger import get_logger
from server.schemas.fraud import (
    FraudAnalysisReport,
    InspectDocumentsRequest,
    PdfForensicsResult,
)

logger = get_logger("server.controllers.fraud")


class FraudController:
    """Controller handling forensic document analysis and tamper detection requests."""

    @staticmethod
    def inspect_documents(payload: InspectDocumentsRequest) -> FraudAnalysisReport:
        """
        Audits an extracted document set across identifier, mathematical,
        physical weight, and temporal paradox forensic rules.
        """
        if not payload.documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payload must contain shipment document data under 'documents'.",
            )

        try:
            return FraudDetectionEngine.audit_extracted_documents(
                documents=payload.documents,
                scenario_title=payload.scenario_title,
            )
        except Exception as exc:
            logger.error("Fraud inspection failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Forensic fraud detection error: {str(exc)}",
            ) from exc

    @staticmethod
    async def inspect_pdf_file(file: UploadFile) -> PdfForensicsResult:
        """Performs digital file and metadata forensics on an uploaded PDF document."""
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF documents are supported for binary digital forensics.",
            )

        try:
            content = await file.read()
            return FraudDetectionEngine.audit_pdf_file(
                pdf_input=content,
                filename=file.filename,
            )
        except Exception as exc:
            logger.error("Digital PDF forensic inspection failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"PDF forensics failure: {str(exc)}",
            ) from exc
