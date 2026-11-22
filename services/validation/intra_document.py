"""
Stage 1: Document-Specific (Intra-Document) Validation Rules.

Validates the internal consistency, arithmetic accuracy, and mandatory fields
of each export document before cross-document reconciliation.
"""

from __future__ import annotations

from typing import Any

from services.validation.models import IntraDocumentCheckResult, ValidationStatus
from services.validation.normalizers import parse_numeric


def validate_commercial_invoice_internal(data: dict[str, Any]) -> list[IntraDocumentCheckResult]:
    """Validates Commercial Invoice internal consistency."""
    results: list[IntraDocumentCheckResult] = []
    doc_type = "Commercial Invoice"

    # 1. Mandatory Fields Check
    mandatory = ["invoice_number", "invoice_date", "currency", "total_invoice_amount"]
    missing = [field for field in mandatory if not data.get(field)]
    if not data.get("exporter_seller", {}).get("name"):
        missing.append("exporter_seller.name")
    if not data.get("consignee_importer", {}).get("name"):
        missing.append("consignee_importer.name")

    if missing:
        results.append(
            IntraDocumentCheckResult(
                document_type=doc_type,
                check_name="mandatory_fields_presence",
                status=ValidationStatus.FAIL,
                message=f"Missing essential fields: {', '.join(missing)}.",
            )
        )
    else:
        results.append(
            IntraDocumentCheckResult(
                document_type=doc_type,
                check_name="mandatory_fields_presence",
                status=ValidationStatus.PASS,
                message="All mandatory invoice header fields are populated.",
            )
        )

    # 2. Line Items Arithmetic Consistency
    line_items = data.get("line_items") or []
    if line_items:
        calculated_total = 0.0
        math_valid = True
        for item in line_items:
            qty = parse_numeric(item.get("quantity"))
            price = parse_numeric(item.get("unit_price"))
            amount = parse_numeric(item.get("total_amount"))
            if qty is not None and price is not None:
                expected_item_total = round(qty * price, 2)
                if amount is not None and abs(expected_item_total - amount) > 0.05:
                    math_valid = False
                calculated_total += amount if amount is not None else expected_item_total

        reported_total = parse_numeric(data.get("total_invoice_amount"))
        subtotal = parse_numeric(data.get("subtotal"))
        benchmark = subtotal if subtotal is not None else reported_total

        if benchmark is not None and calculated_total > 0:
            if abs(calculated_total - benchmark) > 0.10:
                results.append(
                    IntraDocumentCheckResult(
                        document_type=doc_type,
                        check_name="line_items_arithmetic_consistency",
                        status=ValidationStatus.FAIL,
                        message=(
                            f"Sum of line items ({calculated_total:.2f}) does not match "
                            f"invoice total ({benchmark:.2f})."
                        ),
                    )
                )
            else:
                results.append(
                    IntraDocumentCheckResult(
                        document_type=doc_type,
                        check_name="line_items_arithmetic_consistency",
                        status=ValidationStatus.PASS,
                        message="Line items aggregate arithmetic matches invoice total.",
                    )
                )

    return results


def validate_packing_list_internal(data: dict[str, Any]) -> list[IntraDocumentCheckResult]:
    """Validates Packing List internal consistency."""
    results: list[IntraDocumentCheckResult] = []
    doc_type = "Packing List"

    # 1. Mandatory Fields
    mandatory = ["packing_list_number"]
    missing = [field for field in mandatory if not data.get(field)]
    if not data.get("exporter_seller", {}).get("name"):
        missing.append("exporter_seller.name")

    if missing:
        results.append(
            IntraDocumentCheckResult(
                document_type=doc_type,
                check_name="mandatory_fields_presence",
                status=ValidationStatus.FAIL,
                message=f"Missing packing list fields: {', '.join(missing)}.",
            )
        )
    else:
        results.append(
            IntraDocumentCheckResult(
                document_type=doc_type,
                check_name="mandatory_fields_presence",
                status=ValidationStatus.PASS,
                message="Essential packing list fields are present.",
            )
        )

    # 2. Net Weight vs Gross Weight Logic
    gross_val = parse_numeric(data.get("total_gross_weight", {}).get("value"))
    net_val = parse_numeric(data.get("total_net_weight", {}).get("value"))

    if gross_val is not None and net_val is not None:
        if net_val > gross_val:
            results.append(
                IntraDocumentCheckResult(
                    document_type=doc_type,
                    check_name="weight_logic_consistency",
                    status=ValidationStatus.FAIL,
                    message=f"Net weight ({net_val}) cannot exceed Gross weight ({gross_val}).",
                )
            )
        else:
            results.append(
                IntraDocumentCheckResult(
                    document_type=doc_type,
                    check_name="weight_logic_consistency",
                    status=ValidationStatus.PASS,
                    message=f"Net weight ({net_val}) is valid within Gross weight ({gross_val}).",
                )
            )

    return results


def validate_purchase_order_internal(data: dict[str, Any]) -> list[IntraDocumentCheckResult]:
    """Validates Purchase Order internal consistency."""
    results: list[IntraDocumentCheckResult] = []
    doc_type = "Purchase Order"

    missing = []
    if not data.get("po_number"):
        missing.append("po_number")
    if not data.get("buyer", {}).get("name"):
        missing.append("buyer.name")

    if missing:
        results.append(
            IntraDocumentCheckResult(
                document_type=doc_type,
                check_name="mandatory_fields_presence",
                status=ValidationStatus.FAIL,
                message=f"Missing purchase order fields: {', '.join(missing)}.",
            )
        )
    else:
        results.append(
            IntraDocumentCheckResult(
                document_type=doc_type,
                check_name="mandatory_fields_presence",
                status=ValidationStatus.PASS,
                message="Purchase order mandatory fields populated.",
            )
        )

    return results


def validate_shipping_bill_internal(data: dict[str, Any]) -> list[IntraDocumentCheckResult]:
    """Validates Shipping Bill internal consistency."""
    results: list[IntraDocumentCheckResult] = []
    doc_type = "Shipping Bill"

    missing = []
    if not data.get("shipping_bill_number"):
        missing.append("shipping_bill_number")
    if not data.get("customs_port_code"):
        missing.append("customs_port_code")

    if missing:
        results.append(
            IntraDocumentCheckResult(
                document_type=doc_type,
                check_name="mandatory_fields_presence",
                status=ValidationStatus.FAIL,
                message=f"Missing shipping bill fields: {', '.join(missing)}.",
            )
        )
    else:
        results.append(
            IntraDocumentCheckResult(
                document_type=doc_type,
                check_name="mandatory_fields_presence",
                status=ValidationStatus.PASS,
                message="Shipping bill customs identifier fields are present.",
            )
        )

    return results


def validate_certificate_of_origin_internal(data: dict[str, Any]) -> list[IntraDocumentCheckResult]:
    """Validates Certificate of Origin internal consistency."""
    results: list[IntraDocumentCheckResult] = []
    doc_type = "Certificate of Origin"

    missing = []
    if not data.get("certificate_number"):
        missing.append("certificate_number")
    if not data.get("issuing_authority_or_chamber"):
        missing.append("issuing_authority_or_chamber")

    if missing:
        results.append(
            IntraDocumentCheckResult(
                document_type=doc_type,
                check_name="mandatory_fields_presence",
                status=ValidationStatus.FAIL,
                message=f"Missing certificate of origin fields: {', '.join(missing)}.",
            )
        )
    else:
        results.append(
            IntraDocumentCheckResult(
                document_type=doc_type,
                check_name="mandatory_fields_presence",
                status=ValidationStatus.PASS,
                message="Certificate of Origin authority and identifier present.",
            )
        )

    return results


INTRA_VALIDATORS = {
    "Commercial Invoice": validate_commercial_invoice_internal,
    "Packing List": validate_packing_list_internal,
    "Purchase Order": validate_purchase_order_internal,
    "Shipping Bill": validate_shipping_bill_internal,
    "Certificate of Origin": validate_certificate_of_origin_internal,
}


def run_intra_document_validation(document_type: str, data: dict[str, Any]) -> list[IntraDocumentCheckResult]:
    """Dispatches to the appropriate document-specific internal validator."""
    validator = INTRA_VALIDATORS.get(document_type)
    if validator:
        return validator(data)
    return []
