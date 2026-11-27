"""
Document Repository for Supabase customs_documents persistence.
Encapsulates all database operations, supporting optional organization scoping
while preserving backward-compatible signatures.
"""

from __future__ import annotations

from typing import Any
from server.config.settings import get_settings
from server.database.supabase import get_supabase_client
from server.logging.logger import get_logger

logger = get_logger("server.repositories.document")


class DocumentRepository:
    """
    Repository class providing CRUD operations for customs_documents table in Supabase.
    """

    def __init__(self, table_name: str | None = None) -> None:
        settings = get_settings()
        self.table_name = table_name or settings.SUPABASE_TABLE_NAME or "customs_documents"

    def store_extracted_document(
        self,
        filename: str,
        document_type: str,
        extracted_data: dict[str, Any],
        organization_id: str | None = None,
        created_by: str | None = None,
    ) -> dict[str, Any]:
        """
        Stores extracted Gemini JSON data into Supabase PostgreSQL.
        Includes optional organization_id and created_by when present in schema.
        """
        if not filename or not filename.strip():
            raise ValueError("Filename cannot be empty when storing in Supabase.")

        if not document_type or not document_type.strip():
            raise ValueError("Document type cannot be empty when storing in Supabase.")

        if not extracted_data or not isinstance(extracted_data, dict):
            raise ValueError("Extracted data must be a non-empty dictionary.")

        client = get_supabase_client()
        record: dict[str, Any] = {
            "filename": filename.strip(),
            "document_type": document_type.strip(),
            "extracted_data": extracted_data,
        }
        if organization_id:
            record["organization_id"] = organization_id
        if created_by:
            record["created_by"] = created_by

        try:
            response = client.table(self.table_name).insert(record).execute()
            if not response.data:
                logger.warning("Supabase insert succeeded but returned no record data.")
                return record

            inserted = response.data[0] if isinstance(response.data, list) else response.data
            logger.info(
                "Successfully stored document '%s' (%s) in Supabase table '%s'.",
                filename,
                document_type,
                self.table_name,
            )
            return inserted
        except Exception as exc:
            # Graceful fallback if customs_documents doesn't have Phase 2 org columns yet
            if (organization_id or created_by) and (
                "organization_id" in str(exc) or "created_by" in str(exc)
            ):
                legacy_record = {
                    "filename": filename.strip(),
                    "document_type": document_type.strip(),
                    "extracted_data": extracted_data,
                }
                response = client.table(self.table_name).insert(legacy_record).execute()
                return response.data[0] if response.data else legacy_record

            logger.error(
                "Failed to store document '%s' in Supabase table '%s': %s",
                filename,
                self.table_name,
                exc,
            )
            raise RuntimeError(
                f"Failed to store document in Supabase table '{self.table_name}': {str(exc)}"
            ) from exc

    def fetch_extracted_documents(
        self,
        filename: str | None = None,
        document_type: str | None = None,
        organization_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Retrieves stored document records from Supabase, strictly filtered by organization_id when supplied.
        """
        client = get_supabase_client()

        try:
            query = client.table(self.table_name).select("*")
            if organization_id:
                query = query.eq("organization_id", organization_id)
            if filename:
                query = query.eq("filename", filename)
            if document_type:
                query = query.eq("document_type", document_type)

            response = query.order("created_at", desc=True).limit(limit).execute()
            return response.data or []
        except Exception as exc:
            logger.error("Failed to fetch documents from Supabase: %s", exc)
            raise RuntimeError(f"Failed to fetch documents from Supabase: {str(exc)}") from exc


_default_repository = DocumentRepository()


def store_extracted_document(
    filename: str,
    document_type: str,
    extracted_data: dict[str, Any],
    table_name: str | None = None,
    organization_id: str | None = None,
    created_by: str | None = None,
) -> dict[str, Any]:
    repo = DocumentRepository(table_name=table_name) if table_name else _default_repository
    return repo.store_extracted_document(
        filename,
        document_type,
        extracted_data,
        organization_id=organization_id,
        created_by=created_by,
    )


def fetch_extracted_documents(
    filename: str | None = None,
    document_type: str | None = None,
    table_name: str | None = None,
    organization_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    repo = DocumentRepository(table_name=table_name) if table_name else _default_repository
    return repo.fetch_extracted_documents(
        filename=filename,
        document_type=document_type,
        organization_id=organization_id,
        limit=limit,
    )
