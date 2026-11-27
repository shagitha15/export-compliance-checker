"""
Controller for LangGraph Export Customs Compliance AI Agent.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict
from fastapi import HTTPException, status

from server.agents.workflow import build_compliance_agent
from server.agents.state import CustomsComplianceAgentState
from server.logging.logger import get_logger
from server.schemas.agent import (
    AgentAnalysisResponse,
    AgentAnalyzeRequest,
    AgentSummary,
)

logger = get_logger("server.controllers.agent")


class AgentController:
    """Controller orchestrating the LangGraph AI compliance agent."""

    _compiled_agent = None

    @classmethod
    def get_agent(cls):
        """Returns singleton compiled LangGraph workflow instance."""
        if cls._compiled_agent is None:
            cls._compiled_agent = build_compliance_agent()
        return cls._compiled_agent

    @classmethod
    def analyze_shipment(cls, payload: AgentAnalyzeRequest) -> AgentAnalysisResponse:
        """
        Executes the 10-node LangGraph export customs compliance workflow.
        """
        if not payload.documents and not payload.files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payload must supply either 'documents' or 'files' for agent analysis.",
            )

        execution_id = f"agt_{uuid.uuid4().hex[:10]}"
        shipment_id = payload.shipment_id or f"SHP-{uuid.uuid4().hex[:8].upper()}"

        initial_state: CustomsComplianceAgentState = {
            "execution_id": execution_id,
            "shipment_id": shipment_id,
            "scenario_title": payload.scenario_title,
            "extracted_documents": payload.documents or {},
            "uploaded_files": payload.files or [],
            "generate_pdf": payload.generate_pdf,
            "execution_history": [],
            "reasons": [],
            "recommendations": [],
            "critical_fraud_flag": False,
        }

        try:
            agent = cls.get_agent()
            final_state: CustomsComplianceAgentState = agent.invoke(initial_state)

            val = final_state.get("cross_document_results")
            gov = final_state.get("statutory_results")
            fraud = final_state.get("fraud_results")
            missing = final_state.get("missing_documents") or []
            extracted = final_state.get("extracted_documents") or {}

            passed_checks = val.summary.passed if val and val.summary else 0
            failed_checks = val.summary.failed if val and val.summary else 0
            is_stat_compliant = (
                gov.overall_government_compliance.value == "COMPLIANT"
                if gov and hasattr(gov, "overall_government_compliance")
                else True
            )
            fraud_risk = fraud.overall_risk_level.value if fraud else "GENUINE"
            auth_score = fraud.overall_authenticity_score if fraud else 100.0

            summary = AgentSummary(
                documents_evaluated=len(extracted),
                missing_documents=missing,
                passed_checks=passed_checks,
                failed_checks=failed_checks,
                statutory_compliant=is_stat_compliant,
                fraud_risk_level=fraud_risk,
                authenticity_score=auth_score,
            )

            has_pdf = bool(final_state.get("pdf_report_bytes"))

            return AgentAnalysisResponse(
                execution_id=execution_id,
                shipment_id=shipment_id,
                scenario_title=payload.scenario_title,
                overall_compliance_status=final_state.get("overall_compliance_status", "APPROVED_FOR_EXPORT"),
                compliance_score=final_state.get("compliance_score", 100.0),
                critical_fraud_flag=final_state.get("critical_fraud_flag", False),
                summary=summary,
                reasons=final_state.get("reasons") or [],
                recommendations=final_state.get("recommendations") or [],
                cross_document_validation=val,
                government_compliance=gov,
                fraud_analysis=fraud,
                pdf_report_available=has_pdf,
                pdf_report_filename=final_state.get("pdf_report_filename"),
                execution_stages=final_state.get("execution_history") or [],
            )

        except Exception as exc:
            logger.error("LangGraph compliance agent execution failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI Agent workflow failure: {str(exc)}",
            ) from exc
