"""
Pinecone Vector Database Service for Indian Export Customs Regulations.

Provides index provisioning, rule embedding persistence, and semantic vector search
with metadata filtering. Includes an in-memory fallback for local/offline testing.
"""

from __future__ import annotations

import json
import logging
import math
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_INDEX_NAME = "export-customs-rules"
DEFAULT_NAMESPACE = "indian-export-regulations-v1"
VECTOR_DIMENSION = 768
VECTOR_METRIC = "cosine"

# In-memory vector store for fallback / offline execution
_LOCAL_VECTOR_STORE: list[dict[str, Any]] = []


def get_pinecone_client() -> Pinecone:
    """Initializes and returns the Pinecone client."""
    load_dotenv(override=True)
    api_key = os.getenv("PINECONE_API_KEY")

    if not api_key or api_key == "your_pinecone_api_key_here":
        raise ValueError(
            "PINECONE_API_KEY is not configured in .env. "
            "Please provide a valid Pinecone API key."
        )

    return Pinecone(api_key=api_key)


def get_or_create_index(index_name: str | None = None) -> Any:
    """
    Connects to the specified Pinecone index, creating it if it does not already exist.
    """
    target_name = index_name or os.getenv("PINECONE_INDEX_NAME", DEFAULT_INDEX_NAME)
    pc = get_pinecone_client()

    existing_indexes = [idx["name"] for idx in pc.list_indexes()]

    if target_name not in existing_indexes:
        logger.info("Index '%s' not found. Creating Pinecone serverless index...", target_name)
        cloud = os.getenv("PINECONE_CLOUD", "aws")
        region = os.getenv("PINECONE_REGION", "us-east-1")
        pc.create_index(
            name=target_name,
            dimension=VECTOR_DIMENSION,
            metric=VECTOR_METRIC,
            spec=ServerlessSpec(cloud=cloud, region=region),
        )
        logger.info("Successfully created Pinecone index '%s'.", target_name)

    return pc.Index(target_name)


def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculates cosine similarity between two float vectors."""
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def upsert_rules_to_pinecone(
    records: list[dict[str, Any]],
    index_name: str | None = None,
    namespace: str | None = None,
) -> int:
    """
    Upserts vector records to Pinecone. Each record must contain:
    - id: str
    - values: list[float]
    - metadata: dict[str, Any]
    """
    target_namespace = namespace or os.getenv("PINECONE_NAMESPACE", DEFAULT_NAMESPACE)

    # Always keep in local store as cache / fallback
    global _LOCAL_VECTOR_STORE
    _LOCAL_VECTOR_STORE = records.copy()

    try:
        index = get_or_create_index(index_name)
        # Prepare vectors for Pinecone batch upsert
        vectors_to_upsert = [
            {
                "id": rec["id"],
                "values": rec["values"],
                "metadata": rec["metadata"],
            }
            for rec in records
        ]
        index.upsert(vectors=vectors_to_upsert, namespace=target_namespace)
        logger.info("Successfully upserted %d rules to Pinecone index.", len(records))
        return len(records)
    except Exception as exc:
        logger.warning(
            "Pinecone upsert encountered an issue (%s). Using local in-memory fallback.",
            exc,
        )
        return len(records)


def query_regulatory_rules(
    query_vector: list[float],
    top_k: int = 4,
    hs_prefix: str | None = None,
    index_name: str | None = None,
    namespace: str | None = None,
) -> list[dict[str, Any]]:
    """
    Performs semantic vector search against regulatory rules with optional HS code filtering.

    Args:
        query_vector: 768-dimensional embedding vector of the search query.
        top_k: Maximum number of matching rules to retrieve.
        hs_prefix: Optional HS code prefix filter (e.g. '8483').

    Returns:
        list[dict[str, Any]]: Matching rules with metadata and similarity score.
    """
    target_namespace = namespace or os.getenv("PINECONE_NAMESPACE", DEFAULT_NAMESPACE)

    # Try Pinecone query first
    try:
        index = get_or_create_index(index_name)
        filter_dict = None
        if hs_prefix:
            filter_dict = {
                "applicable_hs_prefixes": {"$in": ["ALL", hs_prefix, hs_prefix[:2]]}
            }

        response = index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
            namespace=target_namespace,
            filter=filter_dict,
        )

        matches = []
        for match in response.get("matches", []):
            matches.append(
                {
                    "rule_id": match["id"],
                    "score": match["score"],
                    "metadata": match.get("metadata", {}),
                }
            )
        if matches:
            return matches

    except Exception as exc:
        logger.debug("Pinecone query bypassed or unavailable (%s). Executing local search.", exc)

    # Fallback to local in-memory search
    results = []
    for rec in _LOCAL_VECTOR_STORE:
        meta = rec.get("metadata", {})
        # Filter by HS prefix if requested
        if hs_prefix:
            prefixes = meta.get("applicable_hs_prefixes", [])
            if "ALL" not in prefixes and hs_prefix not in prefixes and hs_prefix[:2] not in prefixes:
                continue

        sim = _cosine_similarity(query_vector, rec["values"])
        results.append(
            {
                "rule_id": rec["id"],
                "score": round(sim, 4),
                "metadata": meta,
            }
        )

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]
