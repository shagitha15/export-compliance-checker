"""
Re-export of Supabase service functions from the root supabase_service module.
"""

from supabase_service import (
    fetch_extracted_documents,
    get_supabase_client,
    store_extracted_document,
)

__all__ = [
    "get_supabase_client",
    "store_extracted_document",
    "fetch_extracted_documents",
]
