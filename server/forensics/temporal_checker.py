"""
Chronological and Temporal Paradox Forensics Verifier.
Validates sequential logic across trade documents: PO Date <= Invoice Date <= Shipping Bill / COO Date.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from server.schemas.fraud import AnomalyCategory, AnomalySeverity, DocumentAnomaly


DATE_PATTERNS = [
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
]


def parse_date_robust(date_str: Any) -> Optional[datetime]:
    """Attempts to parse a trade document date string using common global formats."""
    if not date_str or not isinstance(date_str, str):
        return None

    clean = date_str.strip()
    clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", clean)  # Remove ordinals like 1st, 2nd

    for pattern in DATE_PATTERNS:
        try:
            return datetime.strptime(clean, pattern)
        except ValueError:
            continue
    return None


def verify_chronological_sequence(documents: Dict[str, Any]) -> List[DocumentAnomaly]:
    """Audits cross-document date ordering for impossible temporal paradoxes."""
    anomalies: List[DocumentAnomaly] = []

    ci = documents.get("Commercial Invoice") or {}
    po = documents.get("Purchase Order") or {}
    sb = documents.get("Shipping Bill") or {}
    coo = documents.get("Certificate of Origin") or {}

    ci_date = parse_date_robust(ci.get("invoice_date") or ci.get("date"))
    po_date = parse_date_robust(po.get("po_date") or po.get("order_date") or po.get("date"))
    sb_date = parse_date_robust(sb.get("shipping_bill_date") or sb.get("date"))
    coo_date = parse_date_robust(coo.get("certificate_date") or coo.get("issue_date") or coo.get("date"))

    # Check 1: PO Date <= Invoice Date
    if po_date and ci_date and po_date > ci_date:
        anomalies.append(
            DocumentAnomaly(
                anomaly_id="FRD_DATE_PO_INV_011",
                category=AnomalyCategory.TEMPORAL_PARADOX,
                severity=AnomalySeverity.HIGH,
                rule_name="Temporal Paradox: Purchase Order Dated After Commercial Invoice",
                description=(
                    "Chronological sequence violation: Buyer Purchase Order date succeeds the Commercial Invoice date. "
                    "Commercial contracts must be agreed upon prior to or on the date of final invoice issuance."
                ),
                evidence=(
                    f"Purchase Order date '{po_date.strftime('%Y-%m-%d')}' is later than Commercial Invoice date "
                    f"'{ci_date.strftime('%Y-%m-%d')}' (gap: {(po_date - ci_date).days} days)."
                ),
                remediation="Align contract execution dates so buyer purchase order precedes commercial invoicing.",
                document_type="Commercial Invoice",
                field_name="invoice_date",
            )
        )

    # Check 2: Invoice Date <= Shipping Bill Date
    if ci_date and sb_date and ci_date > sb_date:
        anomalies.append(
            DocumentAnomaly(
                anomaly_id="FRD_DATE_INV_SB_012",
                category=AnomalyCategory.TEMPORAL_PARADOX,
                severity=AnomalySeverity.HIGH,
                rule_name="Temporal Paradox: Invoice Dated After Customs Shipping Bill",
                description=(
                    "Chronological sequence violation: Commercial Invoice date succeeds the official Customs Shipping Bill date. "
                    "Customs export declarations under Section 50 can only be lodged against an already-existing invoice."
                ),
                evidence=(
                    f"Commercial Invoice date '{ci_date.strftime('%Y-%m-%d')}' post-dates Shipping Bill date "
                    f"'{sb_date.strftime('%Y-%m-%d')}' (gap: {(ci_date - sb_date).days} days)."
                ),
                remediation="Ensure Commercial Invoice is issued prior to or on the date of ICEGATE Shipping Bill filing.",
                document_type="Shipping Bill",
                field_name="shipping_bill_date",
            )
        )

    # Check 3: Invoice Date <= Certificate of Origin Date
    if ci_date and coo_date and ci_date > coo_date:
        anomalies.append(
            DocumentAnomaly(
                anomaly_id="FRD_DATE_INV_COO_013",
                category=AnomalyCategory.TEMPORAL_PARADOX,
                severity=AnomalySeverity.MEDIUM,
                rule_name="Temporal Paradox: Certificate of Origin Precedes Commercial Invoice",
                description=(
                    "Chronological sequence anomaly: Chamber of Commerce Certificate of Origin issue date precedes the Commercial Invoice date. "
                    "Authorized chambers cannot certify an invoice that has not yet been generated."
                ),
                evidence=(
                    f"Certificate of Origin issued on '{coo_date.strftime('%Y-%m-%d')}' prior to Commercial Invoice date "
                    f"'{ci_date.strftime('%Y-%m-%d')}'."
                ),
                remediation="Request updated Chamber Certificate of Origin citing the correct Commercial Invoice issue date.",
                document_type="Certificate of Origin",
                field_name="certificate_date",
            )
        )

    return anomalies
