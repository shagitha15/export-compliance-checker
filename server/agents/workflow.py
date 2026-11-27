"""
LangGraph Workflow Assembly for Export Customs Compliance AI Agent.
Constructs a deterministic, stateful graph uniting all 10 compliance nodes.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from server.agents.nodes import (
    completeness_check_node,
    compliance_decision_node,
    cross_document_validation_node,
    document_classification_node,
    document_input_node,
    fake_document_detection_node,
    final_response_node,
    ocr_data_extraction_node,
    pdf_report_generation_node,
    statutory_verification_node,
)
from server.agents.state import CustomsComplianceAgentState


def route_after_input(state: CustomsComplianceAgentState) -> str:
    """Routes to OCR extraction if raw files were passed, otherwise skips straight to completeness check."""
    if state.get("input_type") == "RAW_FILES":
        return "document_classification"
    return "completeness_check"


def build_compliance_agent():
    """
    Compiles and returns the LangGraph executable workflow for export compliance auditing.
    """
    workflow = StateGraph(CustomsComplianceAgentState)

    # 1. Register all 10 specialized workflow nodes
    workflow.add_node("document_input", document_input_node)
    workflow.add_node("document_classification", document_classification_node)
    workflow.add_node("ocr_data_extraction", ocr_data_extraction_node)
    workflow.add_node("completeness_check", completeness_check_node)
    workflow.add_node("cross_document_validation", cross_document_validation_node)
    workflow.add_node("statutory_verification", statutory_verification_node)
    workflow.add_node("fake_document_detection", fake_document_detection_node)
    workflow.add_node("compliance_decision", compliance_decision_node)
    workflow.add_node("pdf_report_generation", pdf_report_generation_node)
    workflow.add_node("final_response", final_response_node)

    # 2. Configure edges and conditional branches
    workflow.add_edge(START, "document_input")

    workflow.add_conditional_edges(
        "document_input",
        route_after_input,
        {
            "document_classification": "document_classification",
            "completeness_check": "completeness_check",
        },
    )

    workflow.add_edge("document_classification", "ocr_data_extraction")
    workflow.add_edge("ocr_data_extraction", "completeness_check")

    # Domain audit pipeline
    workflow.add_edge("completeness_check", "cross_document_validation")
    workflow.add_edge("cross_document_validation", "statutory_verification")
    workflow.add_edge("statutory_verification", "fake_document_detection")
    workflow.add_edge("fake_document_detection", "compliance_decision")

    # Finalization and certificate synthesis
    workflow.add_edge("compliance_decision", "pdf_report_generation")
    workflow.add_edge("pdf_report_generation", "final_response")
    workflow.add_edge("final_response", END)

    return workflow.compile()
