"""
External Integrations Layer.
Integrates with external APIs and services: Google Gemini, Pinecone Vector DB, and Embeddings.
"""

from server.integrations.gemini import get_gemini_client
from server.integrations.embeddings import (
    generate_embedding,
    generate_embeddings_batch,
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL,
)
from server.integrations.pinecone import (
    get_pinecone_client,
    get_or_create_index,
    upsert_rules_to_pinecone,
    query_regulatory_rules,
)

__all__ = [
    "get_gemini_client",
    "generate_embedding",
    "generate_embeddings_batch",
    "EMBEDDING_DIMENSION",
    "EMBEDDING_MODEL",
    "get_pinecone_client",
    "get_or_create_index",
    "upsert_rules_to_pinecone",
    "query_regulatory_rules",
]
