"""
Automated Document Classifier.
Intelligently classifies customs trade documents into one of the 5 canonical types:
- Commercial Invoice
- Packing List
- Purchase Order
- Shipping Bill
- Certificate of Origin
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple
from server.schemas.upload import DocumentType
from server.logging.logger import get_logger

logger = get_logger("server.document_intelligence.classifier")

# Priority keywords and weighted patterns
CLASSIFICATION_RULES: Dict[DocumentType, Dict[str, Any]] = {
    DocumentType.COMMERCIAL_INVOICE: {
        "title_patterns": [
            r"commercial\s+invoice",
            r"tax\s+invoice",
            r"export\s+invoice",
            r"proforma\s+invoice",
            r"invoice\s+no",
        ],
        "keywords": [
            "lut arn",
            "exporter (seller)",
            "buyer (if other than consignee)",
            "terms of delivery",
            "terms of payment",
            "ad code",
            "bank details",
            "unit price",
            "fob value",
            "cgst rule 46",
            "integrated tax",
        ],
        "filename_hints": ["invoice", "ci", "comm_inv"],
    },
    DocumentType.PACKING_LIST: {
        "title_patterns": [
            r"packing\s+list",
            r"packing\s+note",
            r"package\s+list",
        ],
        "keywords": [
            "packing list",
            "total packages",
            "net weight",
            "gross weight",
            "package no",
            "case no",
            "dimensions",
            "total net weight",
            "total gross weight",
            "no. & kind of pkgs",
        ],
        "filename_hints": ["packing", "pl", "pkg"],
    },
    DocumentType.PURCHASE_ORDER: {
        "title_patterns": [
            r"purchase\s+order",
            r"p\.?o\.?\s+number",
            r"buyer\s+order",
        ],
        "keywords": [
            "purchase order",
            "po number",
            "vendor",
            "vendor supplier",
            "buyer",
            "order date",
            "delivery terms",
            "order reference",
        ],
        "filename_hints": ["po", "purchase", "order"],
    },
    DocumentType.SHIPPING_BILL: {
        "title_patterns": [
            r"shipping\s+bill",
            r"bill\s+of\s+export",
            r"icegate\s+shipping",
        ],
        "keywords": [
            "shipping bill",
            "customs port code",
            "section 50",
            "ritc hs code",
            "let export order",
            "leo",
            "export duty",
            "scheme code",
            "port of loading",
            "fob value",
        ],
        "filename_hints": ["shipping", "sb", "bill_of_export"],
    },
    DocumentType.CERTIFICATE_OF_ORIGIN: {
        "title_patterns": [
            r"certificate\s+of\s+origin",
            r"country\s+of\s+origin",
            r"origin\s+declaration",
        ],
        "keywords": [
            "certificate of origin",
            "issuing authority",
            "chamber of commerce",
            "origin criterion",
            "wholly obtained",
            "non-preferential",
            "declaration by the exporter",
            "certification by competent authority",
        ],
        "filename_hints": ["coo", "origin", "certificate"],
    },
}


def classify_document_type(text: str, filename: str | None = None) -> DocumentType:
    """
    Classifies raw OCR text and optional filename into a canonical customs DocumentType.

    Args:
        text: Extracted page text or full document text.
        filename: Optional client filename for secondary heuristic weighting.

    Returns:
        DocumentType: The classified document type.
    """
    if not text and not filename:
        return DocumentType.COMMERCIAL_INVOICE

    lower_text = text.lower() if text else ""
    first_page_header = lower_text[:1500] if len(lower_text) > 1500 else lower_text
    lower_filename = filename.lower() if filename else ""

    scores: Dict[DocumentType, int] = {doc_type: 0 for doc_type in DocumentType}

    for doc_type, rules in CLASSIFICATION_RULES.items():
        # 1. Title patterns in header (High weight: +10)
        for pattern in rules["title_patterns"]:
            if re.search(pattern, first_page_header, re.IGNORECASE):
                scores[doc_type] += 10
                break

        # 2. Structural keywords (Moderate weight: +2 each)
        for kw in rules["keywords"]:
            if kw in lower_text:
                scores[doc_type] += 2

        # 3. Filename hints (Secondary weight: +3)
        for hint in rules["filename_hints"]:
            if hint in lower_filename:
                scores[doc_type] += 3
                break

    # Find highest score
    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_doc_type, best_score = sorted_scores[0]

    logger.debug(
        "Classification scores for '%s': %s -> Selected: %s (Score: %d)",
        filename or "unknown",
        scores,
        best_doc_type.value,
        best_score,
    )

    if best_score > 0:
        return best_doc_type

    # Default to Commercial Invoice if undetermined
    logger.info("Could not determine document type with confidence; defaulting to Commercial Invoice.")
    return DocumentType.COMMERCIAL_INVOICE
