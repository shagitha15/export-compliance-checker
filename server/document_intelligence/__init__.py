"""
Document Intelligence Module.
"""

from server.document_intelligence.schemas import DOCUMENT_SCHEMAS
from server.document_intelligence.prompts import build_extraction_prompt, format_extracted_text
from server.document_intelligence.extractor import extract_document_data
from server.document_intelligence.classifier import classify_document_type

__all__ = [
    "DOCUMENT_SCHEMAS",
    "build_extraction_prompt",
    "format_extracted_text",
    "extract_document_data",
    "classify_document_type",
]
