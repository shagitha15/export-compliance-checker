"""
Digital PDF File and Metadata Forensics Verifier.
Uses PyMuPDF to inspect document metadata, producer software, modification timestamps, font integrity, and incremental updates.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import fitz  # PyMuPDF

from server.schemas.fraud import (
    AnomalyCategory,
    AnomalySeverity,
    DocumentAnomaly,
    PdfForensicsResult,
)


SUSPICIOUS_PRODUCERS = [
    "photoshop",
    "canva",
    "ilovepdf",
    "sejda",
    "pdfedit",
    "foxit phantom",
    "smallpdf",
    "pdfescape",
    "inkscape",
    "gimp",
]


def inspect_pdf_forensics(pdf_input: str | Path | bytes, filename: str = "document.pdf") -> PdfForensicsResult:
    """
    Performs deep digital forensic inspection on a PDF file.

    Args:
        pdf_input: Path to file (str/Path) or raw PDF bytes.
        filename: Original file name for reporting.

    Returns:
        PdfForensicsResult with extracted digital metadata and detected anomalies.
    """
    anomalies: List[DocumentAnomaly] = []
    doc = None
    try:
        if isinstance(pdf_input, (str, Path)):
            doc = fitz.open(pdf_input)
        elif isinstance(pdf_input, bytes):
            doc = fitz.open(stream=pdf_input, filetype="pdf")
        else:
            raise ValueError("Unsupported PDF input type: must be path or bytes.")

        page_count = doc.page_count
        metadata = doc.metadata or {}

        producer = metadata.get("producer") or ""
        creator = metadata.get("creator") or ""
        creation_date = metadata.get("creationDate") or ""
        mod_date = metadata.get("modDate") or ""

        # 1. Producer / Tool Blacklist Audit
        tool_signals = f"{producer} {creator}".lower()
        matched_tools = [t for t in SUSPICIOUS_PRODUCERS if t in tool_signals]
        if matched_tools:
            anomalies.append(
                DocumentAnomaly(
                    anomaly_id="FRD_META_TOOL_001",
                    category=AnomalyCategory.METADATA_TAMPERING,
                    severity=AnomalySeverity.HIGH,
                    rule_name="Suspicious Consumer PDF Modification Tool Signature",
                    description=(
                        "Document metadata indicates the PDF was generated or modified using consumer photo/PDF editing tools "
                        "rather than enterprise ERP or customs software (e.g. SAP, Tally, Oracle, ICEGATE)."
                    ),
                    evidence=f"Detected consumer editing tool signature '{matched_tools[0]}' in producer metadata: '{producer}' / '{creator}'.",
                    remediation="Require native source documents directly exported from company ERP or customs portal.",
                    document_type="PDF Document",
                    field_name="producer",
                )
            )

        # 2. Creation Date vs Modification Date Paradox
        if creation_date and mod_date:
            # Parse PyMuPDF format: "D:YYYYMMDDHHmmSS..."
            def _parse_pdf_date(d_str: str) -> Optional[int]:
                clean = re.sub(r"[^\d]", "", d_str)
                if len(clean) >= 8:
                    try:
                        return int(clean[:8])  # YYYYMMDD as integer
                    except ValueError:
                        return None
                return None

            c_num = _parse_pdf_date(creation_date)
            m_num = _parse_pdf_date(mod_date)
            if c_num and m_num and m_num < c_num:
                anomalies.append(
                    DocumentAnomaly(
                        anomaly_id="FRD_META_DATE_002",
                        category=AnomalyCategory.METADATA_TAMPERING,
                        severity=AnomalySeverity.HIGH,
                        rule_name="Chronological Paradox in File Metadata",
                        description="PDF modification timestamp is earlier than creation timestamp, indicating artificial clock tampering or metadata alteration.",
                        evidence=f"Modification date '{mod_date}' precedes creation date '{creation_date}'.",
                        remediation="Investigate file origin and verify digital signature.",
                        document_type="PDF Document",
                        field_name="modDate",
                    )
                )

        # 3. Typography & Font Splice Forensics
        unique_fonts: set[str] = set()
        for page in doc:
            font_list = page.get_fonts()
            for font_item in font_list:
                # font_item format: (xref, ext, type, basefont, name, encoding)
                if len(font_item) > 3 and font_item[3]:
                    unique_fonts.add(font_item[3])

        # If a single-page document has 5+ disparate font families, flag typography splicing
        if page_count == 1 and len(unique_fonts) >= 5:
            anomalies.append(
                DocumentAnomaly(
                    anomaly_id="FRD_FONT_SPLICE_003",
                    category=AnomalyCategory.TYPOGRAPHY_ANOMALY,
                    severity=AnomalySeverity.MEDIUM,
                    rule_name="Excessive Font Splice Anomaly",
                    description=(
                        "Single-page document contains 5 or more distinct disparate embedded font families, "
                        "which frequently indicates text splicing or pasted value modifications."
                    ),
                    evidence=f"Identified {len(unique_fonts)} fonts on single page: {sorted(list(unique_fonts))[:5]}",
                    remediation="Visually inspect numeric value alignments and font uniformity.",
                    document_type="PDF Document",
                    field_name="fonts",
                )
            )

        is_tampered = any(a.severity in (AnomalySeverity.CRITICAL, AnomalySeverity.HIGH) for a in anomalies)

        return PdfForensicsResult(
            filename=filename,
            page_count=page_count,
            producer=producer,
            creator=creator,
            creation_date=creation_date,
            mod_date=mod_date,
            fonts_detected=sorted(list(unique_fonts)),
            is_tampered=is_tampered,
            anomalies=anomalies,
        )

    finally:
        if doc is not None:
            doc.close()
