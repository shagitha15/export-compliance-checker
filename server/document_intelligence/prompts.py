"""
Prompt Templates and Text Formatting for Customs Document Intelligence.
"""

from __future__ import annotations

import json
from typing import Any


def format_extracted_text(pdf_text: dict[int, str] | str) -> str:
    """Formats page-wise or raw extracted text into an annotated string."""
    if isinstance(pdf_text, dict):
        formatted_pages = []
        for page_num in sorted(pdf_text.keys()):
            content = (pdf_text[page_num] or "").strip()
            formatted_pages.append(f"--- PAGE {page_num} ---\n{content}")
        return "\n\n".join(formatted_pages)
    return str(pdf_text).strip()


def build_extraction_prompt(
    document_type: str,
    formatted_text: str,
    target_schema: dict[str, Any],
) -> str:
    """Constructs a schema-guided extraction prompt for Gemini."""
    return f"""You are an expert customs documentation compliance auditor.
Your job is to extract structured information from the provided {document_type} document text into valid JSON.

TARGET JSON STRUCTURE:
{json.dumps(target_schema, indent=2)}

STRICT EXTRACTION RULES:
1. Extract ONLY information explicitly present in the document text.
2. If any field or value is missing, not mentioned, or ambiguous, set its value to null.
3. NEVER assume, extrapolate, calculate, or invent any information.
4. For numeric values (like amounts, weights, quantities), extract numeric numbers (int or float) where possible, or null if absent.
5. Preserve accurate codes such as HS codes, GSTIN/tax IDs, IEC, port codes, and currency codes.
6. Return ONLY the valid JSON object conforming to the target schema. Do not include markdown fences, code blocks, or explanations.

DOCUMENT TEXT:
{formatted_text}
"""
