"""
Supabase PostgreSQL Service for Export Customs Documentation Compliance Checker.

Handles connection to Supabase and persistence of Gemini-extracted JSON document data.

Recommended Supabase SQL Table Definition:
------------------------------------------
CREATE TABLE IF NOT EXISTS customs_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    document_type TEXT NOT NULL,
    extracted_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client

# Ensure environment variables are loaded
load_dotenv()

logger = logging.getLogger(__name__)

# Cached Supabase client instance
_supabase_client: Client | None = None


def get_supabase_client(force_new: bool = False) -> Client:
    """
    Initializes and returns a Supabase client using credentials from .env.

    Args:
        force_new: If True, forces creation of a new client instance instead of reusing cached.

    Returns:
        Client: Authenticated Supabase client.

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY are missing or set to placeholder values.
    """
    global _supabase_client

    if _supabase_client is not None and not force_new:
        return _supabase_client

    load_dotenv(override=True)

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = (
        os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )

    if not supabase_url or supabase_url.strip() in (
        "",
        "your_supabase_url_here",
        "your_supabase_project_url_here",
    ):
        raise ValueError(
            "SUPABASE_URL is not configured in .env. "
            "Please add your project URL (e.g., https://your-project.supabase.co)."
        )

    if not supabase_key or supabase_key.strip() in (
        "",
        "your_supabase_key_here",
        "your_supabase_api_key_here",
    ):
        raise ValueError(
            "SUPABASE_KEY is not configured in .env. "
            "Please add your Supabase anon or service-role API key."
        )

    try:
        _supabase_client = create_client(supabase_url.strip(), supabase_key.strip())
        logger.info("Supabase client initialized successfully for URL: %s", supabase_url)
        return _supabase_client
    except Exception as exc:
        logger.error("Failed to initialize Supabase client: %s", exc)
        raise RuntimeError(f"Could not connect to Supabase: {str(exc)}") from exc


def store_extracted_document(
    filename: str,
    document_type: str,
    extracted_data: dict[str, Any],
    table_name: str | None = None,
) -> dict[str, Any]:
    """
    Stores extracted Gemini JSON data into the Supabase PostgreSQL database.

    Args:
        filename: Name of the uploaded/processed PDF document.
        document_type: Category (Commercial Invoice, Packing List, Purchase Order, etc.).
        extracted_data: The structured JSON dictionary extracted by Gemini.
        table_name: Optional custom table name; defaults to SUPABASE_TABLE_NAME env or 'customs_documents'.

    Returns:
        dict[str, Any]: The inserted record returned from Supabase.

    Raises:
        ValueError: If required fields are missing or empty.
        RuntimeError: If the insert operation fails.
    """
    if not filename or not filename.strip():
        raise ValueError("Filename cannot be empty when storing in Supabase.")

    if not document_type or not document_type.strip():
        raise ValueError("Document type cannot be empty when storing in Supabase.")

    if not extracted_data or not isinstance(extracted_data, dict):
        raise ValueError("Extracted data must be a non-empty dictionary.")

    client = get_supabase_client()
    target_table = table_name or os.getenv("SUPABASE_TABLE_NAME", "customs_documents")

    record: dict[str, Any] = {
        "filename": filename.strip(),
        "document_type": document_type.strip(),
        "extracted_data": extracted_data,
    }

    try:
        response = client.table(target_table).insert(record).execute()

        if not response.data:
            logger.warning("Supabase insert succeeded but returned no record data.")
            return record

        inserted_record = response.data[0] if isinstance(response.data, list) else response.data
        logger.info(
            "Successfully stored document '%s' (%s) in Supabase table '%s'.",
            filename,
            document_type,
            target_table,
        )
        return inserted_record

    except Exception as exc:
        logger.error(
            "Failed to store document '%s' in Supabase table '%s': %s",
            filename,
            target_table,
            exc,
        )
        raise RuntimeError(
            f"Failed to store document in Supabase table '{target_table}': {str(exc)}"
        ) from exc


def fetch_extracted_documents(
    filename: str | None = None,
    document_type: str | None = None,
    table_name: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Retrieves stored document records from Supabase.

    Args:
        filename: Optional filter by filename.
        document_type: Optional filter by document type.
        table_name: Supabase table name.
        limit: Maximum number of records to return.

    Returns:
        list[dict[str, Any]]: List of matching document records.
    """
    client = get_supabase_client()
    target_table = table_name or os.getenv("SUPABASE_TABLE_NAME", "customs_documents")

    try:
        query = client.table(target_table).select("*")
        if filename:
            query = query.eq("filename", filename)
        if document_type:
            query = query.eq("document_type", document_type)

        response = query.order("created_at", desc=True).limit(limit).execute()
        return response.data or []
    except Exception as exc:
        logger.error("Failed to fetch documents from Supabase: %s", exc)
        raise RuntimeError(f"Failed to fetch documents from Supabase: {str(exc)}") from exc


if __name__ == "__main__":
    import sys

    print("--- Supabase Connection Test ---")
    try:
        client = get_supabase_client()
        print("✓ Supabase client created successfully.")
        print(f"✓ Target table: {os.getenv('SUPABASE_TABLE_NAME', 'customs_documents')}")
    except ValueError as val_err:
        print(f"ℹ Configuration Notice: {val_err}")
    except Exception as err:
        print(f"✗ Connection error: {err}", file=sys.stderr)
