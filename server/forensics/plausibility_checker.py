"""
Mathematical, Physical, and Commercial Plausibility Forensics Verifier.
Verifies line item summation math, invoice value extensions, physical weight laws, and zero-value signals.
"""

from __future__ import annotations

from typing import Any, Dict, List
from server.schemas.fraud import AnomalyCategory, AnomalySeverity, DocumentAnomaly


def verify_mathematical_integrity(ci_data: Dict[str, Any]) -> List[DocumentAnomaly]:
    """Audits commercial invoice for arithmetic errors, forged line-item totals, and subtotal discrepancies."""
    anomalies: List[DocumentAnomaly] = []
    if not ci_data:
        return anomalies

    line_items = ci_data.get("line_items") or []
    calculated_subtotal = 0.0

    for idx, item in enumerate(line_items, start=1):
        try:
            qty = float(item.get("quantity") or 0.0)
            unit_price = float(item.get("unit_price") or 0.0)
            declared_item_total = float(item.get("total_amount") or item.get("total_price") or 0.0)
        except (ValueError, TypeError):
            continue

        expected_item_total = round(qty * unit_price, 2)
        calculated_subtotal += expected_item_total

        # Check line item extension: qty * price == declared_total
        if declared_item_total > 0 and abs(expected_item_total - declared_item_total) > 0.05:
            anomalies.append(
                DocumentAnomaly(
                    anomaly_id=f"FRD_LINE_MATH_007_{idx}",
                    category=AnomalyCategory.NUMERICAL_FORGERY,
                    severity=AnomalySeverity.CRITICAL,
                    rule_name="Line Item Mathematical Inconsistency",
                    description="Calculated line item amount (quantity × unit price) does not match declared total.",
                    evidence=(
                        f"Item #{idx} ('{item.get('description', 'Item')}'): {qty} × {unit_price} = "
                        f"{expected_item_total:.2f}, but declared line amount is {declared_item_total:.2f}."
                    ),
                    remediation="Reconcile billing calculation or re-issue invoice with correct arithmetic extensions.",
                    document_type="Commercial Invoice",
                    field_name=f"line_items[{idx-1}].total_amount",
                )
            )

    # Check subtotal vs sum of line items
    declared_subtotal = ci_data.get("subtotal")
    if declared_subtotal is not None and line_items:
        try:
            declared_subtotal = float(declared_subtotal)
            if abs(calculated_subtotal - declared_subtotal) > 0.10:
                anomalies.append(
                    DocumentAnomaly(
                        anomaly_id="FRD_SUBTOTAL_MISMATCH_007B",
                        category=AnomalyCategory.NUMERICAL_FORGERY,
                        severity=AnomalySeverity.CRITICAL,
                        rule_name="Invoice Subtotal Extension Variance",
                        description="Declared subtotal does not equal the arithmetic sum of individual line item amounts.",
                        evidence=(
                            f"Sum of line items is {calculated_subtotal:.2f}, but declared invoice subtotal is {declared_subtotal:.2f} "
                            f"(variance: {abs(calculated_subtotal - declared_subtotal):.2f})."
                        ),
                        remediation="Correct invoice subtotal to accurately match sum of line items.",
                        document_type="Commercial Invoice",
                        field_name="subtotal",
                    )
                )
        except (ValueError, TypeError):
            pass

    # Check total invoice amount vs subtotal
    declared_total = ci_data.get("total_invoice_amount")
    if declared_total is not None:
        try:
            total_val = float(declared_total)
            if total_val <= 0:
                anomalies.append(
                    DocumentAnomaly(
                        anomaly_id="FRD_ZERO_VAL_010",
                        category=AnomalyCategory.NUMERICAL_FORGERY,
                        severity=AnomalySeverity.HIGH,
                        rule_name="Zero or Negative Commercial Invoice Valuation",
                        description="Commercial trade invoices for international export consignments cannot declare zero or negative total value.",
                        evidence=f"Declared total invoice amount is {total_val}.",
                        remediation="Commercial export declarations must declare authentic transaction value for customs valuation.",
                        document_type="Commercial Invoice",
                        field_name="total_invoice_amount",
                    )
                )
        except (ValueError, TypeError):
            pass

    return anomalies


def verify_physical_weight_laws(doc_data: Dict[str, Any], doc_type: str = "Packing List") -> List[DocumentAnomaly]:
    """Enforces fundamental physical law: Net Weight <= Gross Weight."""
    anomalies: List[DocumentAnomaly] = []
    if not doc_data:
        return anomalies

    # Parse gross weight
    gw_raw = doc_data.get("total_gross_weight") or doc_data.get("gross_weight")
    nw_raw = doc_data.get("total_net_weight") or doc_data.get("net_weight")

    def _extract_val(raw: Any) -> float | None:
        if raw is None:
            return None
        if isinstance(raw, dict):
            raw = raw.get("value")
        try:
            return float(raw)
        except (ValueError, TypeError):
            return None

    gw = _extract_val(gw_raw)
    nw = _extract_val(nw_raw)

    if gw is not None and nw is not None:
        if nw > gw:
            anomalies.append(
                DocumentAnomaly(
                    anomaly_id="FRD_WEIGHT_INVERT_009",
                    category=AnomalyCategory.PHYSICAL_ANOMALY,
                    severity=AnomalySeverity.CRITICAL,
                    rule_name="Physical Law Inversion: Net Weight Exceeds Gross Weight",
                    description=(
                        "Physical impossibility: Total Net Weight cannot exceed Total Gross Weight (Gross Weight must include packaging, pallets, and tare weight). "
                        "This is a primary forensic signal of synthetic or hastily altered shipping documentation."
                    ),
                    evidence=f"Declared Net Weight is {nw:.2f} kg, which exceeds Gross Weight of {gw:.2f} kg (difference: {nw - gw:.2f} kg).",
                    remediation="Re-weigh consignment and re-issue Packing List and Shipping Bill with accurate tare weights.",
                    document_type=doc_type,
                    field_name="total_net_weight",
                )
            )

    return anomalies
