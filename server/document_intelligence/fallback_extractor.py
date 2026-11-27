"""
Deterministic PyMuPDF-Text Fallback Extractor for Customs Trade Documents.

Used only when Gemini AI extraction fails after exhausting retries or when the
configured model is unavailable. Extracts explicitly labeled fields from raw
PyMuPDF PDF text without fabricating or guessing missing values.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from server.document_intelligence.prompts import format_extracted_text
from server.document_intelligence.schemas import DOCUMENT_SCHEMAS

_CURRENCY_RE = r"(USD|EUR|GBP|INR|JPY|AED|SGD|AUD|CAD|CHF)"
_INCOTERMS_RE = r"\b(EXW|FCA|CPT|CIP|DAP|DPU|DDP|FAS|FOB|CFR|CIF)\b"
_GSTIN_RE = r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b"


def _search_first(text: str, patterns: list[str], flags: int = re.IGNORECASE) -> str | None:
    """Returns the first cleaned regex group match from text, or None."""
    for pat in patterns:
        match = re.search(pat, text, flags)
        if match:
            val = match.group(1).strip(" \t\r\n:;-|")
            if val:
                return val
    return None


def _parse_number(raw: str | None) -> float | None:
    """Converts a numeric string (with commas) into a float, or None."""
    if not raw:
        return None
    cleaned = raw.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_int(raw: str | None) -> int | None:
    """Converts a numeric string into an int if valid, or None."""
    num = _parse_number(raw)
    return int(round(num)) if num is not None else None


def _extract_weight(text: str, labels: list[str]) -> dict[str, Any] | None:
    """Extracts a weight value + unit pair if present in text."""
    for label in labels:
        pattern = rf"(?:{label})\s*[:\-]?\s*([\d,]+(?:\.\d+)?)\s*(KG|KGS|MT|TONS|LBS|G)?\b"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = _parse_number(match.group(1))
            if val is not None:
                unit = (match.group(2) or "KG").upper()
                if unit == "KGS":
                    unit = "KG"
                return {"value": val, "unit": unit}
    return None


def _count_populated_fields(obj: Any) -> int:
    """Counts non-empty primitive fields populated beyond top-level document_type."""
    count = 0
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("document_type", "_extraction_metadata"):
                continue
            count += _count_populated_fields(v)
    elif isinstance(obj, list):
        for item in obj:
            count += _count_populated_fields(item)
    elif obj is not None and obj != "":
        count += 1
    return count


def extract_structured_fallback(
    document_type: str,
    pdf_text: dict[int, str] | str,
) -> tuple[dict[str, Any], int]:
    """
    Extracts structured fields deterministically from PyMuPDF-extracted text.

    Returns:
        tuple[dict[str, Any], int]: (schema_aligned_dict, populated_field_count)
    """
    if document_type not in DOCUMENT_SCHEMAS:
        raise ValueError(f"Unsupported document type '{document_type}' for fallback extraction.")

    text = format_extracted_text(pdf_text)
    data = copy.deepcopy(DOCUMENT_SCHEMAS[document_type])

    if not text or not text.strip():
        return data, 0

    # Shared tokens across trade documents
    currency = _search_first(
        text,
        [
            rf"(?:Currency|Curr)\s*[:\-]?\s*{_CURRENCY_RE}\b",
            rf"\b{_CURRENCY_RE}\s*[\d,]+(?:\.\d+)?",
            rf"[\d,]+(?:\.\d+)?\s*{_CURRENCY_RE}\b",
        ],
    )
    if currency:
        currency = currency.upper()

    incoterms = _search_first(
        text,
        [
            rf"(?:Incoterms?|Terms\s+of\s+Delivery)\s*[:\-]?\s*{_INCOTERMS_RE}",
            _INCOTERMS_RE,
        ],
    )
    if incoterms:
        incoterms = incoterms.upper()

    gstin = _search_first(text, [_GSTIN_RE], flags=0)
    iec = _search_first(
        text,
        [r"(?:IEC(?:\s*No\.?|\s*Number|\s*Code)?)\s*[:\-]?\s*([A-Z0-9]{10})\b"],
    )
    hs_code = _search_first(
        text,
        [r"(?:RITC\s*/?\s*HS\s*Code|RITC\s*Code|HS\s*Code|HSN)\s*[:\-]?\s*(\d{4,8}(?:\.\d{2,4})?)"],
    )
    inv_no = _search_first(
        text,
        [
            r"(?:Invoice\s*(?:No\.?|Number|Ref\.?)|Inv\.?\s*No\.?)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]{2,})",
        ],
    )
    inv_date = _search_first(
        text,
        [
            r"(?:Invoice\s*Date)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2}|\d{2}[/\-]\d{2}[/\-]\d{2,4})",
        ],
    )
    exporter_name = _search_first(
        text,
        [r"(?:Exporter(?:\s*/\s*Seller)?|Seller|Vendor(?:\s*/\s*Supplier)?)\s*[:\-]\s*([^\n|,;]+)"],
    )
    consignee_name = _search_first(
        text,
        [r"(?:Consignee(?:\s*/\s*Importer)?|Importer(?:\s*/\s*Consignee)?|Buyer)\s*[:\-]\s*([^\n|,;]+)"],
    )
    port_loading = _search_first(
        text,
        [r"(?:Port\s+of\s+Loading)\s*[:\-]?\s*([A-Za-z0-9 ,\-]+)"],
    )
    port_discharge = _search_first(
        text,
        [r"(?:Port\s+of\s+Discharge)\s*[:\-]?\s*([A-Za-z0-9 ,\-]+)"],
    )

    if document_type == "Commercial Invoice":
        data["invoice_number"] = inv_no
        data["invoice_date"] = inv_date
        data["currency"] = currency
        data["incoterms"] = incoterms
        data["port_of_loading"] = port_loading
        data["port_of_discharge"] = port_discharge
        data["exporter_seller"]["name"] = exporter_name
        data["exporter_seller"]["tax_id_or_gstin"] = gstin
        data["consignee_importer"]["name"] = consignee_name

        total_amt = _parse_number(
            _search_first(
                text,
                [
                    r"(?:Total\s+Invoice\s*(?:Amount|Value)|Grand\s*Total|Total\s*Amount|Total)\s*[:\-]?\s*(?:USD|EUR|GBP|INR|JPY)?\s*([\d,]+(?:\.\d+)?)",
                ],
            )
        )
        data["total_invoice_amount"] = total_amt
        data["subtotal"] = _parse_number(
            _search_first(text, [r"(?:Subtotal)\s*[:\-]?\s*(?:USD|EUR|GBP|INR|JPY)?\s*([\d,]+(?:\.\d+)?)"])
        )
        qty = _parse_number(_search_first(text, [r"(?:Quantity|Qty)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)"]))
        if hs_code or qty is not None:
            data["line_items"] = [
                {
                    "item_no": 1,
                    "description": _search_first(text, [r"(?:Description(?:\s+of\s+Goods)?)\s*[:\-]\s*([^\n]+)"]),
                    "hs_code": hs_code,
                    "quantity": qty,
                    "unit": _search_first(text, [r"(?:Unit)\s*[:\-]?\s*([A-Z]{2,6})\b"]),
                    "unit_price": _parse_number(
                        _search_first(text, [r"(?:Unit\s*Price)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)"])
                    ),
                    "total_amount": total_amt,
                }
            ]
        else:
            data["line_items"] = []

        if re.search(r"Section\s*50|truthful|actual\s+price", text, re.IGNORECASE):
            data["declaration_and_signatory"]["declaration_text"] = "Statutory declaration text detected in PDF."

    elif document_type == "Packing List":
        data["packing_list_number"] = _search_first(
            text,
            [r"(?:Packing\s*List\s*(?:No\.?|Number)|PL\s*No\.?)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]{2,})"],
        )
        data["packing_list_date"] = _search_first(
            text, [r"(?:Packing\s*List\s*Date|Date)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2}|\d{2}[/\-]\d{2}[/\-]\d{2,4})"]
        )
        data["invoice_reference_number"] = inv_no
        data["exporter_seller"]["name"] = exporter_name
        data["consignee"]["name"] = consignee_name
        data["port_of_loading"] = port_loading
        data["port_of_discharge"] = port_discharge
        data["total_packages_count"] = _parse_int(
            _search_first(text, [r"(?:Total\s*Packages(?:\s*Count)?|Packages)\s*[:\-]?\s*(\d+)"])
        )
        gross_w = _extract_weight(text, [r"Total\s*Gross\s*Weight", r"Gross\s*Weight", r"Gross\s*Wt\.?"])
        net_w = _extract_weight(text, [r"Total\s*Net\s*Weight", r"Net\s*Weight", r"Net\s*Wt\.?"])
        if gross_w:
            data["total_gross_weight"] = gross_w
        if net_w:
            data["total_net_weight"] = net_w
        data["packages"] = []

    elif document_type == "Purchase Order":
        data["po_number"] = _search_first(
            text,
            [r"(?:Purchase\s*Order\s*(?:No\.?|Number)|PO\s*(?:No\.?|Number))\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]{2,})"],
        )
        data["po_date"] = _search_first(
            text, [r"(?:PO\s*Date|Order\s*Date|Date)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2}|\d{2}[/\-]\d{2}[/\-]\d{2,4})"]
        )
        data["buyer"]["name"] = consignee_name
        data["vendor_supplier"]["name"] = exporter_name
        data["currency"] = currency
        data["incoterms"] = incoterms
        data["total_amount"] = _parse_number(
            _search_first(
                text,
                [r"(?:Total\s*(?:PO\s*)?Amount|Total)\s*[:\-]?\s*(?:USD|EUR|GBP|INR|JPY)?\s*([\d,]+(?:\.\d+)?)"],
            )
        )
        data["line_items"] = []

    elif document_type == "Shipping Bill":
        data["shipping_bill_number"] = _search_first(
            text,
            [r"(?:Shipping\s*Bill\s*(?:No\.?|Number)|SB\s*No\.?)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]{2,})"],
        )
        data["shipping_bill_date"] = _search_first(
            text, [r"(?:Shipping\s*Bill\s*Date|SB\s*Date)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2}|\d{2}[/\-]\d{2}[/\-]\d{2,4})"]
        )
        data["customs_port_code"] = _search_first(
            text,
            [r"(?:Customs\s*Port(?:\s*Code)?|Port\s*Code)\s*[:\-]?\s*([A-Z]{2}[A-Z0-9]{4})\b", r"\b(IN[A-Z]{3}\d)\b"],
        )
        data["iec"] = iec
        data["gstin"] = gstin
        data["invoice_number"] = inv_no
        data["currency"] = currency
        data["fob_value"] = _parse_number(
            _search_first(text, [r"(?:FOB\s*Value|FOB)\s*[:\-]?\s*(?:USD|EUR|GBP|INR|JPY)?\s*([\d,]+(?:\.\d+)?)"])
        )
        data["total_invoice_value"] = _parse_number(
            _search_first(text, [r"(?:Total\s*Invoice\s*Value|Invoice\s*Value)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)"])
        ) or data["fob_value"]
        data["exporter"]["name"] = exporter_name
        data["consignee"]["name"] = consignee_name
        gross_w = _extract_weight(text, [r"Gross\s*Weight", r"Gross\s*Wt\.?"])
        net_w = _extract_weight(text, [r"Net\s*Weight", r"Net\s*Wt\.?"])
        if gross_w:
            data["gross_weight"] = gross_w
        if net_w:
            data["net_weight"] = net_w
        data["items"] = [{"item_no": 1, "ritc_hs_code": hs_code, "fob_value": data["fob_value"]}] if hs_code else []

    elif document_type == "Certificate of Origin":
        data["certificate_number"] = _search_first(
            text,
            [r"(?:Certificate\s*(?:No\.?|Number)|COO\s*No\.?)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]{2,})"],
        )
        data["issue_date"] = _search_first(
            text, [r"(?:Issue\s*Date|Date)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2}|\d{2}[/\-]\d{2}[/\-]\d{2,4})"]
        )
        data["issuing_authority_or_chamber"] = _search_first(
            text,
            [r"(?:Issuing\s*(?:Authority|Chamber)|Chamber\s+of\s+Commerce|Chamber)\s*[:\-]\s*([^\n]+)"],
        )
        data["exporter"]["name"] = exporter_name
        data["importer_or_consignee"]["name"] = consignee_name
        data["origin_criterion"] = _search_first(
            text,
            [r"(?:Origin\s*Criterion|Origin)\s*[:\-]\s*([^\n]+)"],
        )
        data["item_details"] = (
            [{"item_no": 1, "hs_code": hs_code, "invoice_number": inv_no}] if (hs_code or inv_no) else []
        )

    elif document_type == "Bill of Lading":
        data["bl_number"] = _search_first(
            text,
            [r"(?:Bill\s+of\s+Lading\s*(?:No\.?|Number)|B/L\s*No\.?|BL\s*No\.?)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]{2,})"],
        )
        data["bl_date"] = _search_first(
            text, [r"(?:B/L\s*Date|Shipped\s+on\s+Board\s+Date|Date)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2}|\d{2}[/\-]\d{2}[/\-]\d{2,4})"]
        )
        data["invoice_number"] = inv_no
        data["exporter"]["name"] = exporter_name or _search_first(text, [r"(?:Shipper)\s*[:\-]\s*([^\n|,;]+)"])
        data["consignee"]["name"] = consignee_name
        data["port_of_loading"] = port_loading
        data["port_of_discharge"] = port_discharge
        data["vessel_flight_no"] = _search_first(text, [r"(?:Vessel(?:\s*/\s*Voyage)?|Ocean\s+Vessel)\s*[:\-]\s*([^\n]+)"])
        data["total_packages_count"] = _parse_int(
            _search_first(text, [r"(?:Total\s*Packages(?:\s*Count)?|No\.?\s*of\s*Packages)\s*[:\-]?\s*(\d+)"])
        )
        data["hs_code"] = hs_code
        gross_w = _extract_weight(text, [r"Gross\s*Weight", r"Gross\s*Wt\.?"])
        if gross_w:
            data["gross_weight"] = gross_w

    return data, _count_populated_fields(data)
