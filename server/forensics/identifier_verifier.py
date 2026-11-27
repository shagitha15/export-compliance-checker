"""
Tax and Statutory Identifier Forensics Verifier.
Validates Indian GSTIN format and Mod-36 checksum, DGFT IEC structure, and Customs Port Codes.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple
from server.schemas.fraud import AnomalyCategory, AnomalySeverity, DocumentAnomaly

# Official Mod-36 Character Map
GSTIN_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GSTIN_REGEX = re.compile(r"^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
IEC_REGEX = re.compile(r"^(?:[A-Z]{5}[0-9]{4}[A-Z]{1}|[0-9]{10})$")
PORT_CODE_REGEX = re.compile(r"^[A-Z]{2}[A-Z]{3}[0-9A-Z]{1}$")


def calculate_gstin_checksum(gstin_14: str) -> Optional[str]:
    """Calculates official Indian GSTIN 15th check digit using Mod-36 Luhn algorithm."""
    if len(gstin_14) < 14:
        return None

    clean_14 = gstin_14[:14].upper()
    try:
        total = 0
        for i, char in enumerate(clean_14):
            val = GSTIN_CHARS.index(char)
            factor = 1 if (i % 2 == 0) else 2
            prod = val * factor
            total += (prod // 36) + (prod % 36)

        rem = total % 36
        check_code = (36 - rem) % 36
        return GSTIN_CHARS[check_code]
    except (ValueError, IndexError):
        return None


def verify_gstin(gstin: str, doc_type: str = "Commercial Invoice") -> List[DocumentAnomaly]:
    """Audits a 15-character Indian GSTIN for structural validity and checksum integrity."""
    anomalies: List[DocumentAnomaly] = []
    if not gstin or not isinstance(gstin, str):
        return anomalies

    clean = gstin.strip().upper()

    # Check 1: Format & Regex
    if not GSTIN_REGEX.match(clean):
        anomalies.append(
            DocumentAnomaly(
                anomaly_id="FRD_GSTIN_FORMAT_005A",
                category=AnomalyCategory.IDENTIFIER_FRAUD,
                severity=AnomalySeverity.HIGH,
                rule_name="GSTIN Syntax & Structure Malformation",
                description="Indian GSTIN must be exactly 15 characters matching state code, PAN, entity, Z, and checksum.",
                evidence=f"Observed invalid GSTIN format '{clean}' on {doc_type}.",
                remediation="Provide valid 15-character GSTIN registered on the GST portal.",
                document_type=doc_type,
                field_name="tax_id_or_gstin",
            )
        )
        return anomalies

    # Check 2: Mod-36 Checksum
    expected_check = calculate_gstin_checksum(clean[:14])
    actual_check = clean[14]

    if expected_check != actual_check:
        anomalies.append(
            DocumentAnomaly(
                anomaly_id="FRD_GSTIN_CHKSUM_005B",
                category=AnomalyCategory.IDENTIFIER_FRAUD,
                severity=AnomalySeverity.CRITICAL,
                rule_name="Indian GSTIN Mod-36 Checksum Failure",
                description="The 15th check character fails the official Indian GSTN Mod-36 Luhn checksum algorithm, indicating synthetic or forged tax identification.",
                evidence=f"GSTIN '{clean}' check character is '{actual_check}', but calculated Mod-36 check is '{expected_check}'.",
                remediation="Immediate investigation required: Verify GSTIN authenticity on https://services.gst.gov.in.",
                document_type=doc_type,
                field_name="tax_id_or_gstin",
            )
        )

    return anomalies


def verify_iec(iec: str, doc_type: str = "Commercial Invoice") -> List[DocumentAnomaly]:
    """Validates DGFT Importer Exporter Code (IEC) format (10-char PAN or legacy 10-digit)."""
    anomalies: List[DocumentAnomaly] = []
    if not iec or not isinstance(iec, str):
        return anomalies

    clean = iec.strip().upper()
    if not IEC_REGEX.match(clean):
        anomalies.append(
            DocumentAnomaly(
                anomaly_id="FRD_IEC_FORMAT_006",
                category=AnomalyCategory.IDENTIFIER_FRAUD,
                severity=AnomalySeverity.HIGH,
                rule_name="DGFT Importer Exporter Code (IEC) Malformation",
                description="DGFT IEC must be a 10-digit numeric code or 10-character PAN-linked alphanumeric code.",
                evidence=f"Observed malformed IEC '{clean}' on {doc_type}.",
                remediation="Ensure valid 10-character DGFT IEC is declared across all shipping bills.",
                document_type=doc_type,
                field_name="iec",
            )
        )

    return anomalies


def verify_customs_port(port_code: str, doc_type: str = "Shipping Bill") -> List[DocumentAnomaly]:
    """Validates UNECE / Indian Customs Port Code format (e.g. INMAA1, INNSA1)."""
    anomalies: List[DocumentAnomaly] = []
    if not port_code or not isinstance(port_code, str):
        return anomalies

    clean = port_code.strip().upper()
    # Extracts primary 6-char code if port includes description, e.g. "INMAA1 (Chennai Sea)"
    match = re.search(r"\b([A-Z]{2}[A-Z]{3}[0-9A-Z]{1})\b", clean)
    if not match:
        anomalies.append(
            DocumentAnomaly(
                anomaly_id="FRD_PORT_FORMAT_014",
                category=AnomalyCategory.IDENTIFIER_FRAUD,
                severity=AnomalySeverity.MEDIUM,
                rule_name="Customs Port Code Syntax Anomaly",
                description="Customs port code must adhere to 6-character UNECE format (e.g. INMAA1 for Chennai Sea).",
                evidence=f"Observed invalid port code declaration '{clean}' on {doc_type}.",
                remediation="Declare registered ICEGATE 6-character port code.",
                document_type=doc_type,
                field_name="customs_port_code",
            )
        )

    return anomalies
