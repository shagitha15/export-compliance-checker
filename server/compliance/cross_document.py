"""
Stage 2: Cross-Document Validation Rules.
Reconciles and audits common fields across all 5 export customs documents:
- Commercial Invoice, Packing List, Purchase Order, Shipping Bill, Certificate of Origin.
"""

from __future__ import annotations

from typing import Any
from server.compliance.normalizers import (
    clean_string,
    company_names_match,
    normalize_currency,
    normalize_hs_code,
    normalize_identifier,
    normalize_weight_to_kg,
    parse_numeric,
)
from server.schemas.validation import CheckResult, ValidationStatus


def validate_invoice_numbers(docs: dict[str, dict[str, Any]]) -> CheckResult:
    """Rule 1: Reconciles invoice numbers across CI, PL, SB, and COO."""
    check_id = "XDOC_INV_NUM_001"
    rule_name = "Invoice Number Consistency"
    field_name = "invoice_number"
    docs_involved = ["Commercial Invoice", "Packing List", "Shipping Bill", "Certificate of Origin"]

    ci = docs.get("Commercial Invoice")
    if not ci or not ci.get("invoice_number"):
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=docs_involved,
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            message="Check skipped: Commercial Invoice is missing or has no invoice number.",
        )

    ci_inv_raw = clean_string(ci.get("invoice_number"))
    ci_inv_norm = normalize_identifier(ci_inv_raw)
    observed: dict[str, Any] = {"Commercial Invoice": ci_inv_raw}

    # Extract invoice references from comparing documents
    pl = docs.get("Packing List")
    if pl:
        pl_ref = clean_string(pl.get("invoice_reference_number") or pl.get("invoice_number"))
        if pl_ref:
            observed["Packing List"] = pl_ref

    sb = docs.get("Shipping Bill")
    if sb:
        sb_ref = clean_string(sb.get("invoice_number"))
        if sb_ref:
            observed["Shipping Bill"] = sb_ref

    coo = docs.get("Certificate of Origin")
    if coo:
        coo_items = coo.get("item_details") or []
        coo_ref = ""
        for it in coo_items:
            if it.get("invoice_number"):
                coo_ref = clean_string(it["invoice_number"])
                break
        if coo_ref:
            observed["Certificate of Origin"] = coo_ref

    bl = docs.get("Bill of Lading")
    if bl:
        bl_ref = clean_string(bl.get("invoice_number"))
        if bl_ref:
            observed["Bill of Lading"] = bl_ref

    if len(observed) == 1:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=["Commercial Invoice"],
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            expected_value=ci_inv_raw,
            observed_values=observed,
            message="Only Commercial Invoice provided; no other documents available to compare invoice numbers.",
        )

    mismatches = []
    for doc_name, val in observed.items():
        if doc_name == "Commercial Invoice":
            continue
        if normalize_identifier(val) != ci_inv_norm:
            mismatches.append(f"{doc_name} cites '{val}'")

    if mismatches:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=list(observed.keys()),
            status=ValidationStatus.FAIL,
            field_name=field_name,
            expected_value=ci_inv_raw,
            observed_values=observed,
            message=f"Invoice number mismatch: Commercial Invoice has '{ci_inv_raw}', but {'; '.join(mismatches)}.",
        )

    return CheckResult(
        check_id=check_id,
        rule_name=rule_name,
        documents_involved=list(observed.keys()),
        status=ValidationStatus.PASS,
        field_name=field_name,
        expected_value=ci_inv_raw,
        observed_values=observed,
        message=f"Invoice reference '{ci_inv_raw}' is verified and matches across {len(observed)} documents.",
    )


def validate_exporter_seller(docs: dict[str, dict[str, Any]]) -> CheckResult:
    """Rule 2: Validates Seller / Exporter identity across all submitted documents."""
    check_id = "XDOC_EXP_PARTY_002"
    rule_name = "Exporter / Seller Identity Verification"
    field_name = "exporter_seller.name"
    docs_involved = ["Commercial Invoice", "Packing List", "Purchase Order", "Shipping Bill", "Certificate of Origin"]

    ci = docs.get("Commercial Invoice")
    if not ci or not ci.get("exporter_seller", {}).get("name"):
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=docs_involved,
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            message="Check skipped: Commercial Invoice exporter details not available as benchmark.",
        )

    benchmark_name = clean_string(ci["exporter_seller"]["name"])
    observed: dict[str, Any] = {"Commercial Invoice": benchmark_name}

    pl = docs.get("Packing List")
    if pl and pl.get("exporter_seller", {}).get("name"):
        observed["Packing List"] = clean_string(pl["exporter_seller"]["name"])

    po = docs.get("Purchase Order")
    if po and po.get("vendor_supplier", {}).get("name"):
        observed["Purchase Order"] = clean_string(po["vendor_supplier"]["name"])

    sb = docs.get("Shipping Bill")
    if sb and sb.get("exporter", {}).get("name"):
        observed["Shipping Bill"] = clean_string(sb["exporter"]["name"])

    coo = docs.get("Certificate of Origin")
    if coo and coo.get("exporter", {}).get("name"):
        observed["Certificate of Origin"] = clean_string(coo["exporter"]["name"])

    bl = docs.get("Bill of Lading")
    if bl:
        bl_exp = bl.get("shipper", {}).get("name") or bl.get("exporter", {}).get("name")
        if bl_exp:
            observed["Bill of Lading"] = clean_string(bl_exp)

    if len(observed) == 1:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=["Commercial Invoice"],
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            expected_value=benchmark_name,
            observed_values=observed,
            message="No comparing documents provided to verify exporter entity.",
        )

    failures = []
    for doc_name, name in observed.items():
        if doc_name == "Commercial Invoice":
            continue
        if not company_names_match(benchmark_name, name):
            failures.append(f"{doc_name} ('{name}')")

    if failures:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=list(observed.keys()),
            status=ValidationStatus.FAIL,
            field_name=field_name,
            expected_value=benchmark_name,
            observed_values=observed,
            message=f"Exporter name mismatch against Commercial Invoice '{benchmark_name}' in: {', '.join(failures)}.",
        )

    return CheckResult(
        check_id=check_id,
        rule_name=rule_name,
        documents_involved=list(observed.keys()),
        status=ValidationStatus.PASS,
        field_name=field_name,
        expected_value=benchmark_name,
        observed_values=observed,
        message=f"Exporter entity matches across {len(observed)} submitted documents.",
    )


def validate_buyer_consignee(docs: dict[str, dict[str, Any]]) -> CheckResult:
    """Rule 3: Validates Importer / Buyer / Consignee entity across documents."""
    check_id = "XDOC_BUY_PARTY_003"
    rule_name = "Importer / Buyer Identity Verification"
    field_name = "consignee_importer.name"
    docs_involved = ["Commercial Invoice", "Packing List", "Purchase Order", "Shipping Bill", "Certificate of Origin"]

    ci = docs.get("Commercial Invoice")
    if not ci or not ci.get("consignee_importer", {}).get("name"):
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=docs_involved,
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            message="Check skipped: Commercial Invoice consignee details missing.",
        )

    benchmark_name = clean_string(ci["consignee_importer"]["name"])
    observed: dict[str, Any] = {"Commercial Invoice": benchmark_name}

    pl = docs.get("Packing List")
    if pl and pl.get("consignee", {}).get("name"):
        observed["Packing List"] = clean_string(pl["consignee"]["name"])

    po = docs.get("Purchase Order")
    if po and po.get("buyer", {}).get("name"):
        observed["Purchase Order"] = clean_string(po["buyer"]["name"])

    sb = docs.get("Shipping Bill")
    if sb and sb.get("consignee", {}).get("name"):
        observed["Shipping Bill"] = clean_string(sb["consignee"]["name"])

    coo = docs.get("Certificate of Origin")
    if coo and coo.get("importer_or_consignee", {}).get("name"):
        observed["Certificate of Origin"] = clean_string(coo["importer_or_consignee"]["name"])

    bl = docs.get("Bill of Lading")
    if bl and bl.get("consignee", {}).get("name"):
        observed["Bill of Lading"] = clean_string(bl["consignee"]["name"])

    if len(observed) == 1:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=["Commercial Invoice"],
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            expected_value=benchmark_name,
            observed_values=observed,
            message="No secondary documents available to verify buyer/consignee.",
        )

    failures = []
    for doc_name, name in observed.items():
        if doc_name == "Commercial Invoice":
            continue
        if not company_names_match(benchmark_name, name):
            failures.append(f"{doc_name} ('{name}')")

    if failures:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=list(observed.keys()),
            status=ValidationStatus.FAIL,
            field_name=field_name,
            expected_value=benchmark_name,
            observed_values=observed,
            message=f"Consignee/Buyer name mismatch against CI '{benchmark_name}' in: {', '.join(failures)}.",
        )

    return CheckResult(
        check_id=check_id,
        rule_name=rule_name,
        documents_involved=list(observed.keys()),
        status=ValidationStatus.PASS,
        field_name=field_name,
        expected_value=benchmark_name,
        observed_values=observed,
        message=f"Consignee/Buyer entity aligns across {len(observed)} submitted documents.",
    )


def validate_currency_alignment(docs: dict[str, dict[str, Any]]) -> CheckResult:
    """Rule 4: Reconciles billing and declaration currency codes."""
    check_id = "XDOC_CURR_004"
    rule_name = "Currency Code Consistency"
    field_name = "currency"
    docs_involved = ["Commercial Invoice", "Purchase Order", "Shipping Bill"]

    ci = docs.get("Commercial Invoice")
    if not ci or not ci.get("currency"):
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=docs_involved,
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            message="Check skipped: Commercial Invoice currency code missing.",
        )

    expected_curr = normalize_currency(ci["currency"])
    observed: dict[str, Any] = {"Commercial Invoice": expected_curr}

    po = docs.get("Purchase Order")
    if po and po.get("currency"):
        observed["Purchase Order"] = normalize_currency(po["currency"])

    sb = docs.get("Shipping Bill")
    if sb and sb.get("currency"):
        observed["Shipping Bill"] = normalize_currency(sb["currency"])

    if len(observed) == 1:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=["Commercial Invoice"],
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            expected_value=expected_curr,
            observed_values=observed,
            message="No comparing financial documents (PO/SB) provided for currency validation.",
        )

    mismatches = [f"{d}: {c}" for d, c in observed.items() if c != expected_curr]
    if mismatches:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=list(observed.keys()),
            status=ValidationStatus.FAIL,
            field_name=field_name,
            expected_value=expected_curr,
            observed_values=observed,
            message=f"Currency mismatch detected: Expected {expected_curr}, but observed {', '.join(mismatches)}.",
        )

    return CheckResult(
        check_id=check_id,
        rule_name=rule_name,
        documents_involved=list(observed.keys()),
        status=ValidationStatus.PASS,
        field_name=field_name,
        expected_value=expected_curr,
        observed_values=observed,
        message=f"Currency '{expected_curr}' matches across all evaluated documents.",
    )


def validate_item_quantities(docs: dict[str, dict[str, Any]]) -> CheckResult:
    """
    Rule 5: Reconciles line item quantities across CI, PL, PO, and SB.
    Supports partial shipments where CI quantity <= PO quantity.
    """
    check_id = "XDOC_QTY_005"
    rule_name = "Product Quantity Reconciliation"
    field_name = "total_quantity"
    docs_involved = ["Commercial Invoice", "Packing List", "Purchase Order", "Shipping Bill"]

    ci = docs.get("Commercial Invoice")
    if not ci:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=docs_involved,
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            message="Check skipped: Commercial Invoice is required for quantity benchmark.",
        )

    # Compute CI total quantity
    ci_qty = 0.0
    for it in ci.get("line_items") or []:
        val = parse_numeric(it.get("quantity"))
        if val is not None:
            ci_qty += val

    if ci_qty <= 0:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=["Commercial Invoice"],
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            message="Check skipped: Commercial Invoice line items contain no readable quantities.",
        )

    observed: dict[str, Any] = {"Commercial Invoice": ci_qty}

    # PL Quantities
    pl = docs.get("Packing List")
    if pl:
        pl_qty = 0.0
        for it in pl.get("packages") or []:
            val = parse_numeric(it.get("quantity"))
            if val is not None:
                pl_qty += val
        if pl_qty > 0:
            observed["Packing List"] = pl_qty

    # SB Quantities
    sb = docs.get("Shipping Bill")
    if sb:
        sb_qty = 0.0
        for it in sb.get("items") or []:
            val = parse_numeric(it.get("quantity"))
            if val is not None:
                sb_qty += val
        if sb_qty > 0:
            observed["Shipping Bill"] = sb_qty

    # PO Quantities (Partial shipment allowed: CI <= PO)
    po = docs.get("Purchase Order")
    po_qty = None
    if po:
        po_total = 0.0
        for it in po.get("line_items") or []:
            val = parse_numeric(it.get("quantity"))
            if val is not None:
                po_total += val
        if po_total > 0:
            po_qty = po_total
            observed["Purchase Order"] = po_qty

    if len(observed) == 1:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=["Commercial Invoice"],
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            expected_value=ci_qty,
            observed_values=observed,
            message="No secondary documents available to reconcile quantities.",
        )

    discrepancies = []
    # Packing List vs CI must be equal
    if "Packing List" in observed:
        delta = abs(observed["Packing List"] - ci_qty)
        if delta > 0.001:
            discrepancies.append(f"Packing List declares {observed['Packing List']} units (variance: {delta:+.2f})")

    # Shipping Bill vs CI must be equal
    if "Shipping Bill" in observed:
        delta = abs(observed["Shipping Bill"] - ci_qty)
        if delta > 0.001:
            discrepancies.append(f"Shipping Bill declares {observed['Shipping Bill']} units (variance: {delta:+.2f})")

    # PO vs CI: CI must not exceed PO
    if po_qty is not None:
        if ci_qty > (po_qty + 0.001):
            discrepancies.append(f"CI quantity ({ci_qty}) exceeds authorized PO quantity ({po_qty})")

    if discrepancies:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=list(observed.keys()),
            status=ValidationStatus.FAIL,
            field_name=field_name,
            expected_value=ci_qty,
            observed_values=observed,
            message=f"Quantity mismatch detected: {'; '.join(discrepancies)}.",
        )

    return CheckResult(
        check_id=check_id,
        rule_name=rule_name,
        documents_involved=list(observed.keys()),
        status=ValidationStatus.PASS,
        field_name=field_name,
        expected_value=ci_qty,
        observed_values=observed,
        message=f"Quantities ({ci_qty} units) fully reconciled across all submitted documents.",
    )


def validate_hs_codes(docs: dict[str, dict[str, Any]]) -> CheckResult:
    """Rule 6: Validates Harmonized System (HS) code classification (6-digit prefix)."""
    check_id = "XDOC_HS_006"
    rule_name = "HS Code Classification Alignment"
    field_name = "hs_code"
    docs_involved = ["Commercial Invoice", "Shipping Bill", "Certificate of Origin"]

    ci = docs.get("Commercial Invoice")
    if not ci:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=docs_involved,
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            message="Check skipped: Commercial Invoice is required for HS code benchmark.",
        )

    ci_hs_set = set()
    for it in ci.get("line_items") or []:
        h = normalize_hs_code(it.get("hs_code"))
        if h:
            ci_hs_set.add(h)

    if not ci_hs_set:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=["Commercial Invoice"],
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            message="Check skipped: No HS codes found in Commercial Invoice line items.",
        )

    observed: dict[str, Any] = {"Commercial Invoice": sorted(list(ci_hs_set))}

    sb = docs.get("Shipping Bill")
    if sb:
        sb_hs = set()
        for it in sb.get("items") or []:
            h = normalize_hs_code(it.get("ritc_hs_code") or it.get("hs_code"))
            if h:
                sb_hs.add(h)
        if sb_hs:
            observed["Shipping Bill"] = sorted(list(sb_hs))

    coo = docs.get("Certificate of Origin")
    if coo:
        coo_hs = set()
        for it in coo.get("item_details") or []:
            h = normalize_hs_code(it.get("hs_code"))
            if h:
                coo_hs.add(h)
        if coo_hs:
            observed["Certificate of Origin"] = sorted(list(coo_hs))

    bl = docs.get("Bill of Lading")
    if bl:
        bl_hs = set()
        h_top = normalize_hs_code(bl.get("hs_code"))
        if h_top:
            bl_hs.add(h_top)
        for it in bl.get("items") or bl.get("line_items") or []:
            h = normalize_hs_code(it.get("hs_code") or it.get("ritc_hs_code"))
            if h:
                bl_hs.add(h)
        if bl_hs:
            observed["Bill of Lading"] = sorted(list(bl_hs))

    if len(observed) == 1:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=["Commercial Invoice"],
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            expected_value=sorted(list(ci_hs_set)),
            observed_values=observed,
            message="No customs declaration or origin certificates provided to verify HS codes.",
        )

    discrepancies = []
    for doc_name, codes in observed.items():
        if doc_name == "Commercial Invoice":
            continue
        unmatched = set(codes) - ci_hs_set
        if unmatched:
            discrepancies.append(f"{doc_name} introduces divergent HS code(s): {', '.join(unmatched)}")

    if discrepancies:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=list(observed.keys()),
            status=ValidationStatus.FAIL,
            field_name=field_name,
            expected_value=sorted(list(ci_hs_set)),
            observed_values=observed,
            message=f"HS code discrepancy: {'; '.join(discrepancies)}.",
        )

    return CheckResult(
        check_id=check_id,
        rule_name=rule_name,
        documents_involved=list(observed.keys()),
        status=ValidationStatus.PASS,
        field_name=field_name,
        expected_value=sorted(list(ci_hs_set)),
        observed_values=observed,
        message=f"Standard 6-digit HS codes ({', '.join(sorted(ci_hs_set))}) match across documents.",
    )


def validate_weights(docs: dict[str, dict[str, Any]]) -> CheckResult:
    """Rule 7: Validates Total Gross Weight reconciliation across PL, SB, and BL (0.1% tolerance)."""
    check_id = "XDOC_WT_007"
    rule_name = "Weight Reconciliation"
    field_name = "total_gross_weight"
    docs_involved = ["Packing List", "Shipping Bill"]

    pl = docs.get("Packing List")
    sb = docs.get("Shipping Bill")
    bl = docs.get("Bill of Lading")

    pl_gw = (
        normalize_weight_to_kg(
            pl.get("total_gross_weight", {}).get("value"),
            pl.get("total_gross_weight", {}).get("unit"),
        )
        if pl
        else None
    )
    sb_gw = (
        normalize_weight_to_kg(
            sb.get("gross_weight", {}).get("value"),
            sb.get("gross_weight", {}).get("unit"),
        )
        if sb
        else None
    )
    bl_gw_raw = bl.get("gross_weight") if bl else None
    bl_gw = (
        normalize_weight_to_kg(
            bl_gw_raw.get("value") if isinstance(bl_gw_raw, dict) else bl_gw_raw,
            bl_gw_raw.get("unit") if isinstance(bl_gw_raw, dict) else "KG",
        )
        if bl_gw_raw is not None
        else None
    )

    observed: dict[str, Any] = {}
    if pl_gw is not None:
        observed["Packing List (KG)"] = pl_gw
    if sb_gw is not None:
        observed["Shipping Bill (KG)"] = sb_gw
    if bl_gw is not None:
        observed["Bill of Lading (KG)"] = bl_gw

    if len(observed) < 2 or pl_gw is None:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=docs_involved,
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            message="Check skipped: Weight comparison requires Packing List plus Shipping Bill or Bill of Lading.",
        )

    active_docs = [k.replace(" (KG)", "") for k in observed.keys()]
    mismatches = []
    max_delta = 0.0
    for label, weight in observed.items():
        if label == "Packing List (KG)":
            continue
        delta = abs(pl_gw - weight)
        tolerance = max(pl_gw, weight) * 0.001  # 0.1% tolerance
        if delta > tolerance and delta > 0.1:
            max_delta = max(max_delta, delta)
            doc_name = label.replace(" (KG)", "")
            mismatches.append(f"{doc_name} declares {weight} KG (variance: {delta:.2f} KG)")

    if mismatches:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=active_docs,
            status=ValidationStatus.FAIL,
            field_name=field_name,
            expected_value=pl_gw,
            observed_values=observed,
            discrepancy=round(max_delta, 3),
            message=(
                f"Gross weight mismatch against Packing List ({pl_gw} KG): "
                f"{'; '.join(mismatches)} exceeding 0.1% tolerance."
            ),
        )

    return CheckResult(
        check_id=check_id,
        rule_name=rule_name,
        documents_involved=active_docs,
        status=ValidationStatus.PASS,
        field_name=field_name,
        expected_value=pl_gw,
        observed_values=observed,
        message=f"Gross weight ({pl_gw} KG) matches across {', '.join(active_docs)} within 0.1% tolerance.",
    )


def validate_financials(docs: dict[str, dict[str, Any]]) -> CheckResult:
    """Rule 8: Validates financial total valuation across CI, PO, and SB."""
    check_id = "XDOC_FIN_008"
    rule_name = "Financial Valuation Consistency"
    field_name = "total_amount"
    docs_involved = ["Commercial Invoice", "Purchase Order", "Shipping Bill"]

    ci = docs.get("Commercial Invoice")
    if not ci or ci.get("total_invoice_amount") is None:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=docs_involved,
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            message="Check skipped: Commercial Invoice total amount is missing.",
        )

    ci_amount = parse_numeric(ci["total_invoice_amount"])
    if ci_amount is None:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=["Commercial Invoice"],
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            message="Check skipped: Cannot parse numeric invoice amount from Commercial Invoice.",
        )

    observed: dict[str, Any] = {"Commercial Invoice": ci_amount}

    po = docs.get("Purchase Order")
    po_amount = None
    if po and po.get("total_amount") is not None:
        po_amount = parse_numeric(po["total_amount"])
        if po_amount is not None:
            observed["Purchase Order"] = po_amount

    sb = docs.get("Shipping Bill")
    sb_amount = None
    if sb and sb.get("total_invoice_value") is not None:
        sb_amount = parse_numeric(sb["total_invoice_value"])
        if sb_amount is not None:
            observed["Shipping Bill"] = sb_amount

    if len(observed) == 1:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=["Commercial Invoice"],
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            expected_value=ci_amount,
            observed_values=observed,
            message="No secondary financial documents (PO/SB) available to compare valuation.",
        )

    discrepancies = []
    # CI vs PO: CI amount must not exceed authorized PO amount
    if po_amount is not None and ci_amount > (po_amount + 0.05):
        discrepancies.append(
            f"Commercial Invoice total ({ci_amount:.2f}) exceeds Purchase Order authorized limit ({po_amount:.2f})"
        )

    # CI vs SB: Declared invoice value must equal CI total
    if sb_amount is not None and abs(ci_amount - sb_amount) > 0.05:
        discrepancies.append(
            f"Shipping Bill declared invoice value ({sb_amount:.2f}) does not match Commercial Invoice ({ci_amount:.2f})"
        )

    if discrepancies:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=list(observed.keys()),
            status=ValidationStatus.FAIL,
            field_name=field_name,
            expected_value=ci_amount,
            observed_values=observed,
            message=f"Financial valuation mismatch: {'; '.join(discrepancies)}.",
        )

    return CheckResult(
        check_id=check_id,
        rule_name=rule_name,
        documents_involved=list(observed.keys()),
        status=ValidationStatus.PASS,
        field_name=field_name,
        expected_value=ci_amount,
        observed_values=observed,
        message="Financial valuation is consistent across submitted documents.",
    )


def validate_incoterms(docs: dict[str, dict[str, Any]]) -> CheckResult:
    """Rule 9: Validates Incoterms alignment between Commercial Invoice and Purchase Order (or Bill of Lading)."""
    check_id = "XDOC_INCO_009"
    rule_name = "Incoterms Alignment"
    field_name = "incoterms"
    docs_involved = ["Commercial Invoice", "Purchase Order"]

    ci = docs.get("Commercial Invoice")
    po = docs.get("Purchase Order")
    bl = docs.get("Bill of Lading")

    if not ci or (not po and not bl):
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=docs_involved,
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            message="Check skipped: Requires Commercial Invoice plus Purchase Order or Bill of Lading for Incoterms comparison.",
        )

    ci_inco = clean_string(ci.get("incoterms")).upper()
    counter_doc_name = "Purchase Order" if po else "Bill of Lading"
    counter_doc = po if po else bl
    counter_inco = clean_string(
        counter_doc.get("incoterms")
        or counter_doc.get("shipping_terms_incoterms")
        or counter_doc.get("freight_terms")
    ).upper()

    active_docs = ["Commercial Invoice", counter_doc_name]
    if not ci_inco or not counter_inco:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=active_docs,
            status=ValidationStatus.NOT_APPLICABLE,
            field_name=field_name,
            message=f"Check skipped: Incoterms missing in Commercial Invoice or {counter_doc_name}.",
        )

    observed = {"Commercial Invoice": ci_inco, counter_doc_name: counter_inco}

    # Match first 3 letters for standard Incoterms (FOB, CIF, CFR, DDP, EXW)
    if ci_inco[:3] != counter_inco[:3]:
        return CheckResult(
            check_id=check_id,
            rule_name=rule_name,
            documents_involved=active_docs,
            status=ValidationStatus.FAIL,
            field_name=field_name,
            expected_value=counter_inco,
            observed_values=observed,
            message=f"Incoterms conflict: {counter_doc_name} specifies '{counter_inco}', but Invoice billed under '{ci_inco}'.",
        )

    return CheckResult(
        check_id=check_id,
        rule_name=rule_name,
        documents_involved=active_docs,
        status=ValidationStatus.PASS,
        field_name=field_name,
        expected_value=counter_inco,
        observed_values=observed,
        message=f"Incoterms '{ci_inco}' align between Commercial Invoice and {counter_doc_name}.",
    )


CROSS_DOCUMENT_RULES = [
    validate_invoice_numbers,
    validate_exporter_seller,
    validate_buyer_consignee,
    validate_currency_alignment,
    validate_item_quantities,
    validate_hs_codes,
    validate_weights,
    validate_financials,
    validate_incoterms,
]
