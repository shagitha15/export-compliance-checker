"""
Gemini API Integration Service for Export Customs Documentation Compliance Checker.

Uses the official google-genai SDK to extract structured JSON data from export
documents (Commercial Invoice, Packing List, Purchase Order, Shipping Bill,
Certificate of Origin).
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

EXTRACTED_DATA_DIR = Path("extracted_data")
EXTRACTED_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Document-specific extraction schemas and target fields
DOCUMENT_SCHEMAS: dict[str, dict[str, Any]] = {
    "Commercial Invoice": {
        "document_type": "Commercial Invoice",
        "invoice_number": None,
        "invoice_date": None,
        "exporter_seller": {
            "name": None,
            "address": None,
            "tax_id_or_gstin": None,
            "country": None,
        },
        "consignee_importer": {
            "name": None,
            "address": None,
            "tax_id": None,
            "country": None,
        },
        "buyer_other_than_consignee": {
            "name": None,
            "address": None,
        },
        "country_of_origin": None,
        "country_of_final_destination": None,
        "pre_carriage_by": None,
        "place_of_receipt": None,
        "vessel_flight_no": None,
        "port_of_loading": None,
        "port_of_discharge": None,
        "final_destination": None,
        "bill_of_lading_or_awb_no": None,
        "incoterms": None,
        "terms_of_payment": None,
        "currency": None,
        "line_items": [
            {
                "item_no": None,
                "description": None,
                "hs_code": None,
                "quantity": None,
                "unit": None,
                "unit_price": None,
                "total_amount": None,
            }
        ],
        "subtotal": None,
        "freight_charges": None,
        "insurance_charges": None,
        "other_charges": None,
        "total_invoice_amount": None,
        "amount_in_words": None,
        "declaration_and_signatory": {
            "signatory_name": None,
            "designation": None,
            "declaration_text": None,
        },
    },
    "Packing List": {
        "document_type": "Packing List",
        "packing_list_number": None,
        "packing_list_date": None,
        "invoice_reference_number": None,
        "invoice_date": None,
        "exporter_seller": {
            "name": None,
            "address": None,
        },
        "consignee": {
            "name": None,
            "address": None,
        },
        "port_of_loading": None,
        "port_of_discharge": None,
        "final_destination": None,
        "shipping_marks_and_numbers": None,
        "total_packages_count": None,
        "package_type": None,
        "total_gross_weight": {
            "value": None,
            "unit": None,
        },
        "total_net_weight": {
            "value": None,
            "unit": None,
        },
        "total_volume_cbm": {
            "value": None,
            "unit": None,
        },
        "packages": [
            {
                "package_no": None,
                "description": None,
                "quantity": None,
                "unit": None,
                "net_weight": None,
                "gross_weight": None,
                "dimensions": None,
            }
        ],
        "signatory": {
            "name": None,
            "designation": None,
        },
    },
    "Purchase Order": {
        "document_type": "Purchase Order",
        "po_number": None,
        "po_date": None,
        "buyer": {
            "name": None,
            "address": None,
            "contact_person": None,
            "email": None,
            "phone": None,
        },
        "vendor_supplier": {
            "name": None,
            "address": None,
            "contact_person": None,
        },
        "ship_to": {
            "name": None,
            "address": None,
        },
        "bill_to": {
            "name": None,
            "address": None,
        },
        "delivery_date_or_schedule": None,
        "payment_terms": None,
        "incoterms": None,
        "currency": None,
        "line_items": [
            {
                "item_no": None,
                "part_or_sku_no": None,
                "description": None,
                "quantity": None,
                "unit": None,
                "unit_price": None,
                "total_price": None,
            }
        ],
        "subtotal": None,
        "tax_amount": None,
        "shipping_cost": None,
        "total_amount": None,
        "authorized_signature": {
            "name": None,
            "date": None,
        },
    },
    "Shipping Bill": {
        "document_type": "Shipping Bill",
        "shipping_bill_number": None,
        "shipping_bill_date": None,
        "customs_port_code": None,
        "customs_house": None,
        "iec": None,
        "pan": None,
        "gstin": None,
        "ad_code": None,
        "exporter": {
            "name": None,
            "address": None,
            "state": None,
        },
        "consignee": {
            "name": None,
            "address": None,
            "country": None,
        },
        "invoice_number": None,
        "invoice_date": None,
        "total_invoice_value": None,
        "currency": None,
        "fob_value": None,
        "freight_value": None,
        "insurance_value": None,
        "port_of_loading": None,
        "port_of_discharge": None,
        "country_of_destination": None,
        "scheme_code": None,
        "nature_of_cargo": None,
        "gross_weight": {
            "value": None,
            "unit": None,
        },
        "net_weight": {
            "value": None,
            "unit": None,
        },
        "total_containers_or_packages": None,
        "items": [
            {
                "item_no": None,
                "ritc_hs_code": None,
                "description": None,
                "quantity": None,
                "unit": None,
                "unit_rate": None,
                "fob_value": None,
                "drawback_code_or_rate": None,
            }
        ],
    },
    "Certificate of Origin": {
        "document_type": "Certificate of Origin",
        "certificate_number": None,
        "issue_date": None,
        "issuing_authority_or_chamber": None,
        "issuing_country": None,
        "exporter": {
            "name": None,
            "address": None,
            "country": None,
        },
        "producer_or_manufacturer": {
            "name": None,
            "address": None,
            "country": None,
        },
        "importer_or_consignee": {
            "name": None,
            "address": None,
            "country": None,
        },
        "transport_details": {
            "mode_of_transport": None,
            "route": None,
            "vessel_flight_no": None,
            "port_of_loading": None,
            "port_of_discharge": None,
        },
        "origin_criterion": None,
        "preferential_tariff_agreement": None,
        "item_details": [
            {
                "item_no": None,
                "marks_and_numbers": None,
                "description_of_goods": None,
                "hs_code": None,
                "quantity_or_weight": None,
                "invoice_number": None,
                "invoice_date": None,
            }
        ],
        "exporter_declaration": {
            "declaration_text": None,
            "place_and_date": None,
            "signatory_name": None,
        },
        "certification": {
            "certifying_body": None,
            "place_and_date": None,
            "authorized_signature_or_stamp": None,
        },
    },
}


def get_gemini_client() -> genai.Client:
    """
    Initializes and returns the Google GenAI Client using the API key from .env
    and configured for API version v1beta via HttpOptions to support JSON response mode.
    """
    # Ensure fresh load of environment variables
    load_dotenv(override=True)
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY is not configured or is using default placeholder in .env. "
            "Please configure a valid Gemini API key."
        )

    api_version = os.getenv("GEMINI_API_VERSION", "v1beta")
    http_options = types.HttpOptions(api_version=api_version)

    return genai.Client(api_key=api_key, http_options=http_options)


def format_extracted_text(pdf_text: dict[int, str] | str) -> str:
    """Formats page-wise or raw extracted text into an annotated string."""
    if isinstance(pdf_text, dict):
        formatted_pages = []
        for page_num in sorted(pdf_text.keys()):
            content = (pdf_text[page_num] or "").strip()
            formatted_pages.append(f"--- PAGE {page_num} ---\n{content}")
        return "\n\n".join(formatted_pages)
    return str(pdf_text).strip()


def extract_document_data(
    document_type: str,
    pdf_text: dict[int, str] | str,
    source_filename: str | None = None,
    save_to_disk: bool = True,
) -> dict[str, Any]:
    """
    Extracts structured JSON data from export customs document text using Gemini.

    Args:
        document_type: One of the 5 allowed document types.
        pdf_text: Page-wise text dict ({1: "...", 2: "..."}) or plain text string.
        source_filename: Optional filename of the uploaded PDF for logging and saving.
        save_to_disk: If True, persists the extracted JSON to the extracted_data/ directory.

    Returns:
        dict[str, Any]: Extracted structured JSON data conforming to the document schema.

    Raises:
        ValueError: If document_type is unsupported or input text is empty.
        RuntimeError: If Gemini API invocation or JSON parsing fails.
    """
    if document_type not in DOCUMENT_SCHEMAS:
        raise ValueError(
            f"Unsupported document type '{document_type}'. "
            f"Allowed types: {list(DOCUMENT_SCHEMAS.keys())}"
        )

    formatted_text = format_extracted_text(pdf_text)
    if not formatted_text:
        raise ValueError(
            "Extracted text is empty. Cannot extract structured data from an empty document."
        )

    client = get_gemini_client()
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    target_schema = DOCUMENT_SCHEMAS[document_type]

    prompt = f"""You are an expert customs documentation compliance auditor.
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

    try:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0,
        )

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )

        response_text = response.text or ""
        if not response_text.strip():
            raise RuntimeError(f"Gemini API returned an empty response for {document_type}.")

        # Sanitize response if wrapped in markdown code blocks
        clean_json_str = response_text.strip()
        if clean_json_str.startswith("```"):
            clean_json_str = re.sub(r"^```(?:json)?\s*", "", clean_json_str)
            clean_json_str = re.sub(r"\s*```$", "", clean_json_str)

        extracted_json = json.loads(clean_json_str)

    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Gemini response as JSON: %s\nRaw: %s", exc, response_text)
        raise RuntimeError(f"Failed to parse Gemini model response as valid JSON: {exc}") from exc
    except errors.APIError as exc:
        logger.error("Gemini API error (%s): %s", exc.code, exc.message)
        raise RuntimeError(f"Gemini API error [{exc.code}]: {exc.message}") from exc
    except Exception as exc:
        logger.error("Gemini API extraction failed: %s", exc)
        raise RuntimeError(f"Gemini API extraction failed: {str(exc)}") from exc

    # Persist extracted JSON to disk if requested
    if save_to_disk and source_filename:
        stem = Path(source_filename).stem
        output_file = EXTRACTED_DATA_DIR / f"{stem}_extracted.json"
        try:
            with output_file.open("w", encoding="utf-8") as f:
                json.dump(extracted_json, f, indent=2, ensure_ascii=False)
            logger.info("Saved extracted JSON to %s", output_file)
        except Exception as exc:
            logger.warning("Could not persist extracted JSON to %s: %s", output_file, exc)

    return extracted_json
