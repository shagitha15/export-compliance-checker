"""
PDF Compliance Report Generation Engine.
Uses PyMuPDF (fitz) to render publication-quality Export Customs Compliance Certificates
for both single-shipment dashboard audits and 5-document batch uploads.
"""

from __future__ import annotations

import textwrap
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import fitz  # PyMuPDF

from server.schemas.report import GeneratePdfReportRequest, ShipmentDetails


# Color Palette (RGB tuples 0.0 to 1.0)
COLOR_PRIMARY_DARK = (0.15, 0.09, 0.11)    # Deep rose-espresso #26181d
COLOR_ACCENT_BLUSH = (0.72, 0.20, 0.33)    # Primary blush rose #b83253
COLOR_BG_LIGHT     = (0.98, 0.96, 0.96)    # Soft blush eggshell #faf6f6
COLOR_BORDER       = (0.94, 0.84, 0.85)    # Border blush #f0d5da
COLOR_TEXT_MAIN    = (0.12, 0.11, 0.13)    # High-contrast charcoal
COLOR_TEXT_MUTED   = (0.42, 0.39, 0.41)    # Muted metadata
COLOR_TEXT_LIGHT   = (1.00, 1.00, 1.00)    # White

# Status Colors
COLOR_PASS_BG      = (0.92, 0.99, 0.96)
COLOR_PASS_BORDER  = (0.65, 0.95, 0.82)
COLOR_PASS_TEXT    = (0.02, 0.37, 0.27)

COLOR_FAIL_BG      = (1.00, 0.94, 0.95)
COLOR_FAIL_BORDER  = (0.99, 0.80, 0.83)
COLOR_FAIL_TEXT    = (0.62, 0.07, 0.22)

COLOR_WARN_BG      = (1.00, 0.97, 0.90)
COLOR_WARN_BORDER  = (0.98, 0.83, 0.48)
COLOR_WARN_TEXT    = (0.65, 0.38, 0.04)

COLOR_NA_BG        = (0.95, 0.96, 0.96)
COLOR_NA_BORDER    = (0.88, 0.90, 0.92)
COLOR_NA_TEXT      = (0.28, 0.32, 0.36)

PAGE_WIDTH = 595.3
PAGE_HEIGHT = 842.0
MARGIN_X = 36.0
CONTENT_RIGHT = 559.0
CONTENT_WIDTH = CONTENT_RIGHT - MARGIN_X
FOOTER_LIMIT_Y = 785.0


def _wrap(text: Any, width: int = 96) -> list[str]:
    """Safely wraps arbitrary values to clean single-line chunks without crashing."""
    if text is None:
        return ["Not Available"]
    s = " ".join(str(text).split())
    if not s:
        return ["Not Available"]
    return textwrap.wrap(s, width=width, break_long_words=True, break_on_hyphens=False) or [s]


def _status_style(status_str: str) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    """Returns (bg, border, text) colors for PASS/FAIL/WARNING/N/A style badges."""
    upper = (status_str or "").upper()
    if upper in ("PASS", "SUCCESS", "COMPLIANT", "GENUINE"):
        return COLOR_PASS_BG, COLOR_PASS_BORDER, COLOR_PASS_TEXT
    if upper in ("FAIL", "FAILED", "NON_COMPLIANT", "HIGH_RISK", "CRITICAL", "HIGH"):
        return COLOR_FAIL_BG, COLOR_FAIL_BORDER, COLOR_FAIL_TEXT
    if upper in ("WARNING", "PARTIAL_SUCCESS", "ADVISORY", "SUSPICIOUS", "DUPLICATE", "MEDIUM"):
        return COLOR_WARN_BG, COLOR_WARN_BORDER, COLOR_WARN_TEXT
    return COLOR_NA_BG, COLOR_NA_BORDER, COLOR_NA_TEXT


def _draw_page_header(page: fitz.Page, title: str, subtitle: str) -> float:
    """Draws consistent top branding banner on a page."""
    page.draw_rect(fitz.Rect(0, 0, PAGE_WIDTH, 56), color=None, fill=COLOR_PRIMARY_DARK)
    page.draw_rect(fitz.Rect(0, 54, PAGE_WIDTH, 56), color=None, fill=COLOR_ACCENT_BLUSH)
    page.insert_text(fitz.Point(MARGIN_X, 26), title, fontsize=12.5, fontname="helv", color=COLOR_TEXT_LIGHT)
    page.insert_text(fitz.Point(MARGIN_X, 42), subtitle, fontsize=8.0, fontname="helv", color=(0.87, 0.71, 0.75))
    return 68.0


def _draw_page_footer(page: fitz.Page, page_num: int, total_pages: int, ref_id: str) -> None:
    """Draws bottom confidential customs footer with page numbering."""
    footer_y = 810.0
    page.draw_line(fitz.Point(MARGIN_X, footer_y - 8), fitz.Point(CONTENT_RIGHT, footer_y - 8), color=COLOR_BORDER, width=0.75)
    page.insert_text(
        fitz.Point(MARGIN_X, footer_y + 4),
        f"Export Customs Compliance Checker • Reference: {ref_id} • Strictly Confidential",
        fontsize=7.5,
        color=COLOR_TEXT_MUTED,
    )
    page.insert_text(
        fitz.Point(505, footer_y + 4),
        f"Page {page_num} of {total_pages}",
        fontsize=7.5,
        color=COLOR_TEXT_MUTED,
    )


class _ReportCursor:
    """Tracks vertical layout across dynamically paginated A4 pages."""

    def __init__(self, doc: fitz.Document, title: str, subtitle: str) -> None:
        self.doc = doc
        self.title = title
        self.subtitle = subtitle
        self.page = self._new_page()
        self.y = 68.0

    def _new_page(self) -> fitz.Page:
        p = self.doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        _draw_page_header(p, self.title, self.subtitle)
        return p

    def ensure_space(self, height: float, section_subtitle: str | None = None) -> None:
        if self.y + height > FOOTER_LIMIT_Y:
            if section_subtitle:
                self.subtitle = section_subtitle
            self.page = self._new_page()
            self.y = 68.0

    def next_page(self, title: str | None = None, subtitle: str | None = None) -> None:
        if title:
            self.title = title
        if subtitle:
            self.subtitle = subtitle
        self.page = self._new_page()
        self.y = 68.0

    def draw_section_banner(self, text: str, fill: tuple[float, float, float] = COLOR_PRIMARY_DARK, text_color: tuple[float, float, float] = COLOR_TEXT_LIGHT) -> None:
        self.ensure_space(34)
        self.page.draw_rect(fitz.Rect(MARGIN_X, self.y, CONTENT_RIGHT, self.y + 20), color=None, fill=fill)
        self.page.insert_text(fitz.Point(MARGIN_X + 10, self.y + 13.5), text, fontsize=8.0, fontname="helv", color=text_color)
        self.y += 24.0


def _extract_trade_snapshot(
    details: Optional[ShipmentDetails],
    extracted_docs: dict[str, dict[str, Any]],
    extra_info: dict[str, Any],
    gov: Any,
) -> dict[str, str]:
    """Extracts trade & party details from real request/document fields without fabricating values."""
    ci = extracted_docs.get("Commercial Invoice") or {}
    pl = extracted_docs.get("Packing List") or {}
    po = extracted_docs.get("Purchase Order") or {}
    sb = extracted_docs.get("Shipping Bill") or {}
    coo = extracted_docs.get("Certificate of Origin") or {}

    ci_seller = ci.get("exporter_seller") or {}
    sb_exporter = sb.get("exporter") or {}
    coo_exporter = coo.get("exporter") or {}
    pl_seller = pl.get("exporter_seller") or {}

    ci_cons = ci.get("consignee_importer") or {}
    sb_cons = sb.get("consignee") or {}
    coo_cons = coo.get("importer_or_consignee") or {}
    pl_cons = pl.get("consignee") or {}
    po_buyer = po.get("buyer") or {}

    exporter_name = (
        (details.exporter_name if details else None)
        or extra_info.get("exporter_name")
        or ci_seller.get("name")
        or sb_exporter.get("name")
        or coo_exporter.get("name")
        or pl_seller.get("name")
        or "Not Available"
    )
    exporter_iec = (
        (details.exporter_iec if details else None)
        or extra_info.get("exporter_iec")
        or ci_seller.get("iec")
        or sb_exporter.get("iec")
        or sb.get("iec")
        or "Not Available"
    )
    exporter_gstin = (
        (details.exporter_gstin if details else None)
        or extra_info.get("exporter_gstin")
        or ci_seller.get("tax_id_or_gstin")
        or sb.get("gstin")
        or "Not Available"
    )
    consignee_name = (
        (details.consignee_name if details else None)
        or extra_info.get("consignee_name")
        or ci_cons.get("name")
        or sb_cons.get("name")
        or coo_cons.get("name")
        or pl_cons.get("name")
        or po_buyer.get("name")
        or "Not Available"
    )
    destination = (
        (details.destination_country if details else None)
        or extra_info.get("destination_country")
        or ci_cons.get("country")
        or sb.get("country_of_destination")
        or (gov.destination_country if gov and getattr(gov, "destination_country", None) else None)
        or "Not Available"
    )
    invoice_number = (
        (details.invoice_number if details else None)
        or extra_info.get("invoice_number")
        or ci.get("invoice_number")
        or sb.get("invoice_number")
        or pl.get("invoice_reference_number")
        or "Not Available"
    )
    currency = (
        (details.declared_currency if details else None)
        or extra_info.get("currency")
        or ci.get("currency")
        or sb.get("currency")
        or po.get("currency")
        or ""
    )
    raw_val = (
        (details.total_declared_value if details and details.total_declared_value is not None else None)
        if details
        else None
    )
    if raw_val is None:
        raw_val = (
            extra_info.get("total_value")
            or ci.get("total_invoice_amount")
            or ci.get("total_invoice_value")
            or ci.get("subtotal")
            or sb.get("fob_value")
            or sb.get("total_invoice_value")
            or po.get("total_amount")
        )
    if raw_val is not None:
        try:
            val_str = f"{currency} {float(raw_val):,.2f}".strip()
        except (TypeError, ValueError):
            val_str = f"{currency} {raw_val}".strip()
    else:
        val_str = "Not Available"

    incoterms = (
        (details.incoterms if details else None)
        or extra_info.get("incoterms")
        or ci.get("incoterms")
        or po.get("incoterms")
        or "Not Available"
    )

    gross_obj = pl.get("total_gross_weight") or sb.get("gross_weight") or ci.get("total_gross_weight")
    net_obj = pl.get("total_net_weight") or sb.get("net_weight") or ci.get("total_net_weight")

    def _fmt_weight(w: Any) -> str:
        if isinstance(w, dict) and w.get("value") is not None:
            return f"{w.get('value')} {w.get('unit') or 'KG'}"
        if w is not None:
            return str(w)
        return "Not Available"

    hs_codes: list[str] = []
    for item in (ci.get("line_items") or []):
        if item.get("hs_code"):
            hs_codes.append(str(item["hs_code"]))
    for item in (sb.get("items") or []):
        code = item.get("ritc_hs_code") or item.get("hs_code")
        if code:
            hs_codes.append(str(code))
    if gov and getattr(gov, "hs_codes_evaluated", None):
        hs_codes.extend(str(c) for c in gov.hs_codes_evaluated if c)
    unique_hs = ", ".join(dict.fromkeys(hs_codes)) if hs_codes else "Not Available"

    return {
        "exporter_name": str(exporter_name),
        "exporter_iec": str(exporter_iec),
        "exporter_gstin": str(exporter_gstin),
        "consignee_name": str(consignee_name),
        "destination": str(destination),
        "invoice_number": str(invoice_number),
        "declared_value": val_str,
        "incoterms": str(incoterms),
        "po_number": str(po.get("po_number") or extra_info.get("po_number") or "Not Available"),
        "shipping_bill_number": str(sb.get("shipping_bill_number") or extra_info.get("shipping_bill_number") or "Not Available"),
        "port_code": str(sb.get("customs_port_code") or extra_info.get("port_code") or "Not Available"),
        "coo_number": str(coo.get("certificate_number") or extra_info.get("coo_number") or "Not Available"),
        "packages": str(pl.get("total_packages_count") or pl.get("total_packages") or extra_info.get("packages") or "Not Available"),
        "gross_weight": _fmt_weight(gross_obj),
        "net_weight": _fmt_weight(net_obj),
        "hs_codes": unique_hs,
    }


def _build_recommendations(
    request: GeneratePdfReportRequest,
    val: Any,
    gov: Any,
    fraud: dict[str, Any] | None,
    uploaded_docs: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    """Collects missing canonical documents and real actionable recommendations."""
    missing_docs: list[str] = []
    if val and getattr(val, "documents_missing", None):
        missing_docs = list(val.documents_missing)
    elif uploaded_docs:
        canonical = [
            "Commercial Invoice",
            "Packing List",
            "Purchase Order",
            "Shipping Bill",
            "Certificate of Origin",
        ]
        present = {
            d.get("document_type")
            for d in uploaded_docs
            if d.get("status") == "SUCCESS" and d.get("document_type")
        }
        missing_docs = [c for c in canonical if c not in present]

    recs: list[str] = []
    if request.recommendations:
        recs.extend(str(r) for r in request.recommendations if r)

    for item in uploaded_docs:
        st = (item.get("status") or "").upper()
        if st == "FAILED":
            fname = item.get("original_filename") or "Unknown file"
            err = item.get("error") or item.get("error_code") or "Processing failed"
            recs.append(f"Re-upload valid PDF for failed file '{fname}': {err}")
        elif st == "DUPLICATE":
            fname = item.get("original_filename") or "Unknown file"
            recs.append(f"Review duplicate submission '{fname}' and remove redundant file before resubmitting.")

    if missing_docs:
        recs.append(f"Submit missing canonical trade documents for complete 5-document clearance: {', '.join(missing_docs)}.")

    if val and getattr(val, "cross_document_results", None):
        for chk in val.cross_document_results:
            if chk.status.value in ("FAIL", "WARNING"):
                detail = chk.discrepancy or chk.message or "Discrepancy detected"
                recs.append(f"Resolve [{chk.check_id}] {chk.rule_name}: {detail}")

    if gov and getattr(gov, "findings", None):
        for f in gov.findings:
            if f.status.value in ("NON_COMPLIANT", "ADVISORY") and f.action_required:
                recs.append(f"[{f.authority} • {f.para_ref}] {f.action_required}")

    if fraud:
        for anom in fraud.get("anomalies") or []:
            rem = anom.get("remediation")
            rule = anom.get("rule_name") or anom.get("anomaly_id") or "Forensic check"
            if rem:
                recs.append(f"[Fraud Check: {rule}] {rem}")

    # Deduplicate while preserving order
    unique_recs = list(dict.fromkeys(recs))
    return missing_docs, unique_recs


def generate_compliance_pdf_report(request: GeneratePdfReportRequest) -> bytes:
    """
    Renders a multi-page A4 PDF Compliance Audit Certificate from live batch or
    dashboard validation, statutory, and forensic fraud results.
    """
    doc = fitz.open()

    val = request.cross_document_validation
    gov = request.government_compliance
    fraud = request.fraud_analysis if isinstance(request.fraud_analysis, dict) else (
        request.fraud_analysis.model_dump(mode="json") if request.fraud_analysis is not None and hasattr(request.fraud_analysis, "model_dump") else None
    )
    details = request.shipment_details
    uploaded_docs = list(request.uploaded_documents or [])
    extracted_docs = dict(request.extracted_documents or {})
    extra_info = dict(request.extracted_trade_info or {})

    batch_id = request.batch_id or "N/A"
    audit_id = val.audit_id if val else (batch_id if batch_id != "N/A" else "N/A")
    ref_id = batch_id if batch_id != "N/A" else audit_id

    gen_dt_raw = request.report_generated_at
    if gen_dt_raw:
        try:
            dt = datetime.fromisoformat(gen_dt_raw.replace("Z", "+00:00"))
            gen_time = dt.strftime("%d %b %Y, %H:%M UTC")
        except ValueError:
            gen_time = gen_dt_raw
    else:
        gen_time = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")

    if val is not None:
        overall_status = val.overall_compliance_status.value
        total_checks = val.summary.total_checks
        passed_checks = val.summary.passed
        failed_checks = val.summary.failed
        na_checks = val.summary.not_applicable
        applicable = total_checks - na_checks
        pass_pct = round((passed_checks / applicable) * 100) if applicable > 0 else 100
    else:
        overall_status = (request.batch_status or "FAILED").upper()
        total_checks = 0
        passed_checks = 0
        failed_checks = 0
        na_checks = 0
        pass_pct = 0

    badge_bg, badge_border, badge_text = _status_style(overall_status)
    trade = _extract_trade_snapshot(details, extracted_docs, extra_info, gov)
    missing_docs, recommendations = _build_recommendations(request, val, gov, fraud, uploaded_docs)

    cursor = _ReportCursor(
        doc,
        "OFFICIAL EXPORT CUSTOMS COMPLIANCE AUDIT CERTIFICATE",
        "Statutory Audit under Customs Act 1962 • Foreign Trade Policy 2023 • FEMA 1999",
    )

    # =========================================================================
    # SECTION 1: Batch & Audit Metadata Strip + Executive Compliance Summary
    # =========================================================================
    p1 = cursor.page
    y = cursor.y
    p1.draw_rect(fitz.Rect(MARGIN_X, y, CONTENT_RIGHT, y + 36), color=COLOR_BORDER, fill=COLOR_BG_LIGHT)
    p1.insert_text(fitz.Point(46, y + 14), f"Batch ID: {batch_id}", fontsize=8.0, color=COLOR_TEXT_MAIN)
    p1.insert_text(fitz.Point(220, y + 14), f"Audit ID: {audit_id}", fontsize=8.0, color=COLOR_TEXT_MAIN)
    p1.insert_text(fitz.Point(400, y + 14), f"Generated: {gen_time}", fontsize=8.0, color=COLOR_TEXT_MAIN)
    scenario_txt = request.scenario_title or (f"Batch Status: {request.batch_status}" if request.batch_status else "Export Consignment Audit")
    p1.insert_text(fitz.Point(46, y + 28), f"Scope: {scenario_txt[:62]}", fontsize=7.5, color=COLOR_TEXT_MUTED)
    p1.insert_text(fitz.Point(400, y + 28), f"Destination: {trade['destination'][:26]}", fontsize=7.5, color=COLOR_TEXT_MUTED)
    y += 44.0

    # Executive Scorecard Box
    p1.draw_rect(fitz.Rect(MARGIN_X, y, CONTENT_RIGHT, y + 72), color=badge_border, fill=badge_bg)
    p1.insert_text(fitz.Point(48, y + 24), f"OVERALL STATUS: {overall_status}", fontsize=13.5, fontname="helv", color=badge_text)
    if val is not None:
        summary_line = f"Cross-Document Pass Rate: {pass_pct}% ({passed_checks} passed, {failed_checks} failed, {na_checks} N/A)"
    else:
        summary_line = f"Batch Status: {request.batch_status or 'FAILED'} — Cross-document reconciliation did not run (no valid parsed documents)."
    p1.insert_text(fitz.Point(48, y + 41), summary_line[:72], fontsize=8.5, color=COLOR_TEXT_MAIN)

    gov_status = gov.overall_government_compliance.value if gov else "NOT EVALUATED"
    fraud_risk = (fraud.get("overall_risk_level") if fraud else None) or "NOT EVALUATED"
    fraud_score = f"{fraud.get('overall_authenticity_score')}%" if fraud and fraud.get("overall_authenticity_score") is not None else "N/A"
    p1.insert_text(
        fitz.Point(48, y + 56),
        f"Statutory Audit: {gov_status}   |   Fraud Risk: {fraud_risk} (Score: {fraud_score})",
        fontsize=8.0,
        color=COLOR_TEXT_MUTED,
    )

    tiles = [
        ("Checks", str(total_checks)),
        ("Passed", str(passed_checks)),
        ("Failed", str(failed_checks)),
        ("N/A", str(na_checks)),
    ]
    tile_x = 344.0
    for label, val_str in tiles:
        p1.draw_rect(fitz.Rect(tile_x, y + 14, tile_x + 48, y + 56), color=COLOR_BORDER, fill=(1, 1, 1))
        p1.insert_text(fitz.Point(tile_x + 15, y + 32), val_str, fontsize=11.5, color=badge_text)
        p1.insert_text(fitz.Point(tile_x + 6, y + 46), label, fontsize=6.5, color=COLOR_TEXT_MUTED)
        tile_x += 53.0
    cursor.y = y + 84.0

    # =========================================================================
    # SECTION 2: Consignment Parties & Extracted Trade Information
    # =========================================================================
    cursor.ensure_space(126)
    y = cursor.y
    p1 = cursor.page
    p1.draw_rect(fitz.Rect(MARGIN_X, y, CONTENT_RIGHT, y + 114), color=COLOR_BORDER, fill=(1, 1, 1))
    p1.draw_rect(fitz.Rect(MARGIN_X, y, CONTENT_RIGHT, y + 20), color=None, fill=COLOR_BG_LIGHT)
    p1.insert_text(fitz.Point(46, y + 14), "CONSIGNMENT PARTIES & EXTRACTED TRADE INFORMATION", fontsize=8.5, fontname="helv", color=COLOR_ACCENT_BLUSH)

    p1.insert_text(fitz.Point(46, y + 35), f"Exporter (Seller): {trade['exporter_name'][:36]}", fontsize=8.2, color=COLOR_TEXT_MAIN)
    p1.insert_text(fitz.Point(46, y + 49), f"IEC: {trade['exporter_iec'][:18]}  |  GSTIN/Tax: {trade['exporter_gstin'][:20]}", fontsize=7.8, color=COLOR_TEXT_MUTED)
    p1.insert_text(fitz.Point(46, y + 63), f"Invoice Ref: {trade['invoice_number'][:24]}  |  PO Ref: {trade['po_number'][:18]}", fontsize=7.8, color=COLOR_TEXT_MUTED)
    p1.insert_text(fitz.Point(46, y + 77), f"Shipping Bill: {trade['shipping_bill_number'][:20]}  |  Port: {trade['port_code'][:14]}", fontsize=7.8, color=COLOR_TEXT_MUTED)
    p1.insert_text(fitz.Point(46, y + 91), f"HS Codes: {trade['hs_codes'][:38]}", fontsize=7.8, color=COLOR_TEXT_MUTED)
    p1.insert_text(fitz.Point(46, y + 105), f"COO Ref: {trade['coo_number'][:34]}", fontsize=7.8, color=COLOR_TEXT_MUTED)

    p1.insert_text(fitz.Point(312, y + 35), f"Importer/Consignee: {trade['consignee_name'][:32]}", fontsize=8.2, color=COLOR_TEXT_MAIN)
    p1.insert_text(fitz.Point(312, y + 49), f"Destination Country: {trade['destination'][:28]}", fontsize=7.8, color=COLOR_TEXT_MUTED)
    p1.insert_text(fitz.Point(312, y + 63), f"Declared Value: {trade['declared_value'][:30]}", fontsize=7.8, color=COLOR_TEXT_MUTED)
    p1.insert_text(fitz.Point(312, y + 77), f"Incoterms: {trade['incoterms'][:24]}", fontsize=7.8, color=COLOR_TEXT_MUTED)
    p1.insert_text(fitz.Point(312, y + 91), f"Packages: {trade['packages'][:12]}  |  Gross: {trade['gross_weight'][:16]}", fontsize=7.8, color=COLOR_TEXT_MUTED)
    p1.insert_text(fitz.Point(312, y + 105), f"Net Weight: {trade['net_weight'][:28]}", fontsize=7.8, color=COLOR_TEXT_MUTED)
    cursor.y = y + 124.0

    # =========================================================================
    # SECTION 3: Uploaded Document Names & Processing Statuses
    # =========================================================================
    if uploaded_docs:
        cursor.draw_section_banner("UPLOADED DOCUMENTS & BATCH PROCESSING STATUSES", fill=COLOR_BG_LIGHT, text_color=COLOR_ACCENT_BLUSH)
        for idx_doc, item in enumerate(uploaded_docs, start=1):
            fname = item.get("original_filename") or f"Document_{idx_doc}"
            dtype = item.get("document_type") or "Unclassified"
            st = str(item.get("status") or "UNKNOWN").upper()
            size_b = item.get("file_size_bytes")
            size_txt = f"{size_b:,} B" if isinstance(size_b, int) else "N/A"
            err = item.get("error") or ""
            err_lines = _wrap(err, 90) if err else []
            box_h = 24.0 + (len(err_lines) * 10.0)
            cursor.ensure_space(box_h + 4)
            bg, _, fg = _status_style(st)
            cy = cursor.y
            cursor.page.draw_rect(fitz.Rect(MARGIN_X, cy, CONTENT_RIGHT, cy + box_h), color=COLOR_BORDER, fill=(1, 1, 1))
            cursor.page.insert_text(fitz.Point(44, cy + 14), f"{idx_doc}. {fname[:42]}", fontsize=8.0, fontname="helv", color=COLOR_TEXT_MAIN)
            cursor.page.insert_text(fitz.Point(275, cy + 14), f"{dtype[:24]} ({size_txt})", fontsize=7.5, color=COLOR_TEXT_MUTED)
            cursor.page.draw_rect(fitz.Rect(474, cy + 3, 550, cy + 17), color=None, fill=bg)
            cursor.page.insert_text(fitz.Point(482, cy + 13), st[:10], fontsize=7.0, color=fg)
            if err_lines:
                ey = cy + 25.0
                for line in err_lines:
                    cursor.page.insert_text(fitz.Point(52, ey), line, fontsize=7.0, color=COLOR_FAIL_TEXT)
                    ey += 10.0
            cursor.y += box_h + 4.0

    # Canonical 5-document completeness roster
    cursor.ensure_space(116)
    y = cursor.y
    p = cursor.page
    p.draw_rect(fitz.Rect(MARGIN_X, y, CONTENT_RIGHT, y + 112), color=COLOR_BORDER, fill=(1, 1, 1))
    p.draw_rect(fitz.Rect(MARGIN_X, y, CONTENT_RIGHT, y + 20), color=None, fill=COLOR_BG_LIGHT)
    p.insert_text(fitz.Point(46, y + 14), "CUSTOMS TRADE DOCUMENTS STATUS (5 CANONICAL TYPES)", fontsize=8.5, fontname="helv", color=COLOR_ACCENT_BLUSH)

    standard_5_docs = [
        ("Commercial Invoice (CI)", "Commercial valuation, LUT/IGST endorsement, Incoterms."),
        ("Packing List (PL)", "Net & gross weights, package units, quantity reconciliation."),
        ("Purchase Order (PO)", "Buyer contract agreement, order lines, unit pricing."),
        ("Shipping Bill (SB)", "ICEGATE customs declaration, port of loading, RITC HS."),
        ("Certificate of Origin (COO)", "Origin criterion (Wholly Obtained/Non-Preferential), Chamber seal."),
    ]
    evaluated_list = list(val.documents_evaluated) if val else [
        d.get("document_type") for d in uploaded_docs if d.get("status") == "SUCCESS" and d.get("document_type")
    ]
    doc_y = y + 32.0
    for doc_name, doc_desc in standard_5_docs:
        is_submitted = any(d and d.lower() in doc_name.lower() for d in evaluated_list)
        status_txt = "SUBMITTED & VALIDATED" if is_submitted else "OMITTED / MISSING"
        txt_col = COLOR_PASS_TEXT if is_submitted else COLOR_FAIL_TEXT
        p.insert_text(fitz.Point(46, doc_y), f"• {doc_name}:", fontsize=8.0, fontname="helv", color=COLOR_TEXT_MAIN)
        p.insert_text(fitz.Point(195, doc_y), doc_desc[:62], fontsize=7.3, color=COLOR_TEXT_MUTED)
        p.insert_text(fitz.Point(445, doc_y), f"[{status_txt}]", fontsize=7.3, color=txt_col)
        doc_y += 15.5
    cursor.y = y + 122.0

    # =========================================================================
    # SECTION 4: Cross-Document Reconciliation Matrix (PASS / FAIL / WARNING / N/A)
    # =========================================================================
    cursor.next_page(
        "CROSS-DOCUMENT RECONCILIATION AUDIT (16 CANONICAL RULES)",
        "Automated Field-by-Field Consistency Verification Across Trade Documents",
    )

    def _draw_matrix_header() -> None:
        cursor.page.draw_rect(fitz.Rect(MARGIN_X, cursor.y, CONTENT_RIGHT, cursor.y + 20), color=None, fill=COLOR_PRIMARY_DARK)
        cursor.page.insert_text(fitz.Point(46, cursor.y + 14), "CHECK ID", fontsize=8.0, fontname="helv", color=COLOR_TEXT_LIGHT)
        cursor.page.insert_text(fitz.Point(150, cursor.y + 14), "COMPLIANCE RULE DESCRIPTION", fontsize=8.0, fontname="helv", color=COLOR_TEXT_LIGHT)
        cursor.page.insert_text(fitz.Point(476, cursor.y + 14), "AUDIT RESULT", fontsize=8.0, fontname="helv", color=COLOR_TEXT_LIGHT)
        cursor.y += 22.0

    _draw_matrix_header()

    if val and val.cross_document_results:
        for check in val.cross_document_results:
            chk_id = check.check_id
            chk_name = check.rule_name
            chk_status = check.status.value
            row_bg, _, row_txt_col = _status_style(chk_status)

            if cursor.y + 22 > FOOTER_LIMIT_Y:
                cursor.next_page()
                _draw_matrix_header()

            ry = cursor.y
            cursor.page.draw_rect(fitz.Rect(MARGIN_X, ry, CONTENT_RIGHT, ry + 19), color=COLOR_BORDER, fill=(1, 1, 1))
            cursor.page.insert_text(fitz.Point(44, ry + 12.5), chk_id, fontsize=7.3, fontname="helv", color=COLOR_ACCENT_BLUSH)
            cursor.page.insert_text(fitz.Point(150, ry + 12.5), chk_name[:56], fontsize=7.5, color=COLOR_TEXT_MAIN)
            cursor.page.draw_rect(fitz.Rect(466, ry + 2.5, 552, ry + 16.5), color=None, fill=row_bg)
            cursor.page.insert_text(fitz.Point(471, ry + 12.5), chk_status[:14], fontsize=6.8, color=row_txt_col)
            cursor.y += 20.0
    else:
        cursor.page.draw_rect(fitz.Rect(MARGIN_X, cursor.y, CONTENT_RIGHT, cursor.y + 30), color=COLOR_BORDER, fill=COLOR_NA_BG)
        cursor.page.insert_text(
            fitz.Point(46, cursor.y + 18),
            "Cross-document reconciliation was not executed because no valid documents were extracted.",
            fontsize=8.0,
            color=COLOR_NA_TEXT,
        )
        cursor.y += 38.0

    # =========================================================================
    # SECTION 5: Discrepancy Descriptions & Explanations (All Failures / Warnings)
    # =========================================================================
    cursor.y += 12.0
    issues = [
        c for c in (val.cross_document_results if val else [])
        if c.status.value in ("FAIL", "WARNING")
    ]
    if issues:
        cursor.draw_section_banner(
            f"CRITICAL DISCREPANCIES IDENTIFIED ({len(issues)} CHECKS REQUIRING REMEDIATION)",
            fill=COLOR_FAIL_BG,
            text_color=COLOR_FAIL_TEXT,
        )
        for f_check in issues:
            disc_text = f_check.discrepancy or getattr(f_check, "message", None) or "Discrepancy detected"
            exp_text = f_check.message if f_check.discrepancy and f_check.message else ""
            lines_disc = _wrap(f"Discrepancy: {disc_text}", 92)
            lines_exp = _wrap(f"Explanation: {exp_text}", 92) if exp_text else []
            box_h = 20.0 + (len(lines_disc) + len(lines_exp)) * 10.5 + 6.0
            cursor.ensure_space(box_h + 6.0)
            cy = cursor.y
            st_bg, st_border, st_fg = _status_style(f_check.status.value)
            cursor.page.draw_rect(fitz.Rect(MARGIN_X, cy, CONTENT_RIGHT, cy + box_h), color=st_border, fill=(1, 1, 1))
            cursor.page.insert_text(fitz.Point(44, cy + 14), f"• [{f_check.check_id}] {f_check.rule_name}", fontsize=8.0, fontname="helv", color=st_fg)
            cursor.page.draw_rect(fitz.Rect(496, cy + 4, 550, cy + 16), color=None, fill=st_bg)
            cursor.page.insert_text(fitz.Point(504, cy + 13), f_check.status.value, fontsize=6.8, color=st_fg)
            ly = cy + 26.0
            for ln in lines_disc:
                cursor.page.insert_text(fitz.Point(50, ly), ln, fontsize=7.3, color=COLOR_TEXT_MAIN)
                ly += 10.5
            for ln in lines_exp:
                cursor.page.insert_text(fitz.Point(50, ly), ln, fontsize=7.1, color=COLOR_TEXT_MUTED)
                ly += 10.5
            cursor.y += box_h + 6.0
    elif val is not None:
        cursor.ensure_space(42)
        cursor.page.draw_rect(fitz.Rect(MARGIN_X, cursor.y, CONTENT_RIGHT, cursor.y + 34), color=COLOR_PASS_BORDER, fill=COLOR_PASS_BG)
        cursor.page.insert_text(fitz.Point(46, cursor.y + 15), "ZERO DISCREPANCIES DETECTED", fontsize=9.5, fontname="helv", color=COLOR_PASS_TEXT)
        cursor.page.insert_text(
            fitz.Point(46, cursor.y + 27),
            "All evaluated commercial trade documents exhibit consistent fields across weights, values, and entities.",
            fontsize=7.8,
            color=COLOR_TEXT_MAIN,
        )
        cursor.y += 42.0

    # =========================================================================
    # SECTION 6: Fake Document & Forensic Authenticity Detection Results
    # =========================================================================
    cursor.draw_section_banner("FAKE DOCUMENT & FORENSIC AUTHENTICITY DETECTION")
    if fraud:
        risk_lvl = str(fraud.get("overall_risk_level") or "GENUINE")
        auth_score = fraud.get("overall_authenticity_score")
        checks_perf = fraud.get("checks_performed") or []
        anomalies = fraud.get("anomalies") or []
        f_bg, f_border, f_fg = _status_style(risk_lvl)

        cursor.ensure_space(46)
        cy = cursor.y
        cursor.page.draw_rect(fitz.Rect(MARGIN_X, cy, CONTENT_RIGHT, cy + 36), color=f_border, fill=f_bg)
        score_disp = f"{auth_score}%" if auth_score is not None else "N/A"
        cursor.page.insert_text(fitz.Point(46, cy + 15), f"Forensic Risk Level: {risk_lvl}   |   Authenticity Score: {score_disp}", fontsize=8.5, fontname="helv", color=f_fg)
        cursor.page.insert_text(
            fitz.Point(46, cy + 28),
            f"Anomalies Detected: {len(anomalies)}   |   Checks Executed: {', '.join(str(c) for c in checks_perf[:5]) or 'Standard Forensic Suite'}"[:95],
            fontsize=7.3,
            color=COLOR_TEXT_MAIN,
        )
        cursor.y += 42.0

        for anom in anomalies:
            sev = str(anom.get("severity") or "HIGH")
            rname = anom.get("rule_name") or anom.get("anomaly_id") or "Forensic Anomaly"
            desc = anom.get("description") or ""
            evid = anom.get("evidence") or ""
            rem = anom.get("remediation") or ""
            lines = _wrap(desc, 92) + (_wrap(f"Evidence: {evid}", 92) if evid else []) + (_wrap(f"Remediation: {rem}", 92) if rem else [])
            box_h = 20.0 + len(lines) * 10.0 + 4.0
            cursor.ensure_space(box_h + 5.0)
            a_bg, a_border, a_fg = _status_style(sev)
            ay = cursor.y
            cursor.page.draw_rect(fitz.Rect(MARGIN_X, ay, CONTENT_RIGHT, ay + box_h), color=a_border, fill=(1, 1, 1))
            cursor.page.insert_text(fitz.Point(44, ay + 14), f"[{sev}] {rname[:64]}", fontsize=7.8, fontname="helv", color=a_fg)
            ly = ay + 25.0
            for ln in lines:
                cursor.page.insert_text(fitz.Point(50, ly), ln, fontsize=7.0, color=COLOR_TEXT_MAIN)
                ly += 10.0
            cursor.y += box_h + 5.0
    else:
        cursor.ensure_space(34)
        cursor.page.draw_rect(fitz.Rect(MARGIN_X, cursor.y, CONTENT_RIGHT, cursor.y + 26), color=COLOR_BORDER, fill=COLOR_NA_BG)
        cursor.page.insert_text(
            fitz.Point(46, cursor.y + 16),
            "Forensic fraud detection was not run or no extracted documents were available for inspection.",
            fontsize=7.6,
            color=COLOR_NA_TEXT,
        )
        cursor.y += 34.0

    # =========================================================================
    # SECTION 7: Statutory Government Regulatory Findings (DGFT, CBIC, RBI)
    # =========================================================================
    cursor.draw_section_banner("INDIAN STATUTORY REGULATORY VERIFICATION (DGFT • CBIC • RBI)")
    statutory_findings = gov.findings if gov and gov.findings else []
    if statutory_findings:
        for finding in statutory_findings:
            f_bg, _, f_col = _status_style(finding.status.value)
            req_lines = _wrap(f"Requirement: {finding.requirement_summary}", 94)
            ev_lines = _wrap(f"Observed Evidence: {finding.observed_evidence}", 94)
            act_lines = _wrap(f"Action Required: {finding.action_required}", 94) if finding.action_required else []
            box_h = 28.0 + (len(req_lines) + len(ev_lines) + len(act_lines)) * 9.8 + 4.0
            cursor.ensure_space(box_h + 5.0)
            fy = cursor.y
            cursor.page.draw_rect(fitz.Rect(MARGIN_X, fy, CONTENT_RIGHT, fy + box_h), color=COLOR_BORDER, fill=(1, 1, 1))
            cursor.page.insert_text(
                fitz.Point(44, fy + 13),
                f"[{finding.rule_id}] {finding.rule_title[:48]} ({finding.authority})",
                fontsize=7.5,
                fontname="helv",
                color=COLOR_TEXT_MAIN,
            )
            cursor.page.draw_rect(fitz.Rect(470, fy + 3, 552, fy + 16), color=None, fill=f_bg)
            cursor.page.insert_text(fitz.Point(475, fy + 12.5), finding.status.value, fontsize=6.7, color=f_col)
            ly = fy + 24.0
            for ln in req_lines:
                cursor.page.insert_text(fitz.Point(48, ly), ln, fontsize=7.0, color=COLOR_TEXT_MAIN)
                ly += 9.8
            for ln in ev_lines:
                cursor.page.insert_text(fitz.Point(48, ly), ln, fontsize=7.0, color=COLOR_TEXT_MUTED)
                ly += 9.8
            for ln in act_lines:
                cursor.page.insert_text(fitz.Point(48, ly), ln, fontsize=7.0, color=COLOR_FAIL_TEXT)
                ly += 9.8
            ref_txt = f"Legal Ref: {finding.policy_document} ({finding.para_ref})"
            if finding.source_url:
                ref_txt += f" • {finding.source_url}"
            cursor.page.insert_text(fitz.Point(48, ly), ref_txt[:104], fontsize=6.6, color=COLOR_ACCENT_BLUSH)
            cursor.y += box_h + 5.0
    else:
        cursor.ensure_space(34)
        cursor.page.draw_rect(fitz.Rect(MARGIN_X, cursor.y, CONTENT_RIGHT, cursor.y + 26), color=COLOR_BORDER, fill=COLOR_NA_BG)
        cursor.page.insert_text(
            fitz.Point(46, cursor.y + 16),
            "No statutory government regulatory audit findings were available for this report.",
            fontsize=7.6,
            color=COLOR_NA_TEXT,
        )
        cursor.y += 34.0

    # =========================================================================
    # SECTION 8: Missing Documents, Recommendations & Legal Sign-off
    # =========================================================================
    cursor.draw_section_banner("MISSING DOCUMENTS & ACTIONABLE RECOMMENDATIONS", fill=COLOR_BG_LIGHT, text_color=COLOR_ACCENT_BLUSH)
    miss_text = ", ".join(missing_docs) if missing_docs else "None — all 5 canonical export documents accounted for."
    miss_lines = _wrap(f"Missing Canonical Documents: {miss_text}", 94)
    rec_lines: list[str] = []
    if recommendations:
        for idx_r, rec in enumerate(recommendations, start=1):
            rec_lines.extend(_wrap(f"{idx_r}. {rec}", 94))
    else:
        rec_lines.append("No remediation actions required. Proceed with customs filing verification.")

    block_h = 14.0 + (len(miss_lines) + len(rec_lines)) * 10.2
    cursor.ensure_space(block_h + 70.0)
    by = cursor.y
    cursor.page.draw_rect(fitz.Rect(MARGIN_X, by, CONTENT_RIGHT, by + block_h), color=COLOR_BORDER, fill=(1, 1, 1))
    ly = by + 14.0
    for ln in miss_lines:
        cursor.page.insert_text(fitz.Point(46, ly), ln, fontsize=7.4, fontname="helv", color=COLOR_TEXT_MAIN)
        ly += 10.2
    for ln in rec_lines:
        if ly + 12 > FOOTER_LIMIT_Y:
            cursor.next_page()
            ly = cursor.y + 10.0
        cursor.page.insert_text(fitz.Point(46, ly), ln, fontsize=7.2, color=COLOR_TEXT_MUTED)
        ly += 10.2
    cursor.y = ly + 10.0

    # Legal Certification Clause
    cursor.ensure_space(60)
    ly = cursor.y
    cursor.page.draw_rect(fitz.Rect(MARGIN_X, ly, CONTENT_RIGHT, ly + 56), color=COLOR_BORDER, fill=COLOR_BG_LIGHT)
    cursor.page.insert_text(fitz.Point(46, ly + 15), "LEGAL COMPLIANCE DECLARATION & AUDIT INTEGRITY", fontsize=8.0, fontname="helv", color=COLOR_PRIMARY_DARK)
    declaration_para = (
        "This audit certificate validates consignment documentation against the requirements of Section 50 of the "
        "Customs Act 1962, Foreign Trade Policy 2023, and RBI Master Direction on Export Realization. Discrepancies "
        "identified herein must be regularized prior to Let Export Order (LEO) generation."
    )
    cursor.page.insert_text(fitz.Point(46, ly + 29), declaration_para[:125], fontsize=7.0, color=COLOR_TEXT_MUTED)
    cursor.page.insert_text(fitz.Point(46, ly + 40), declaration_para[125:255], fontsize=7.0, color=COLOR_TEXT_MUTED)
    cursor.page.insert_text(fitz.Point(46, ly + 51), "Digitally generated by Export Customs Compliance Checker AI Engine.", fontsize=6.5, color=COLOR_ACCENT_BLUSH)

    # Draw page numbers & footers on every page
    total_p = len(doc)
    for idx, page in enumerate(doc):
        _draw_page_footer(page, idx + 1, total_p, ref_id)

    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes
