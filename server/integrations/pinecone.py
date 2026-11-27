"""
Pinecone Vector Database Integration for Indian Export Customs Regulations.
Provides index provisioning, rule embedding persistence, and semantic vector search.
Includes in-memory fallback for local/offline testing.
"""

from __future__ import annotations

import math
from typing import Any
from pinecone import Pinecone, ServerlessSpec
from server.config.settings import get_settings
from server.logging.logger import get_logger

logger = get_logger("server.integrations.pinecone")

VECTOR_DIMENSION = 768
VECTOR_METRIC = "cosine"

# Cached singleton client instance
_pinecone_client: Pinecone | None = None

# In-memory vector store for fallback / offline execution
_LOCAL_VECTOR_STORE: list[dict[str, Any]] = []


def get_pinecone_client(force_new: bool = False) -> Pinecone:
    """
    Initializes and returns the Pinecone client.
    Implements safe lazy initialization (no side-effects on import).
    """
    global _pinecone_client

    if _pinecone_client is not None and not force_new:
        return _pinecone_client

    settings = get_settings()
    api_key = settings.PINECONE_API_KEY

    if not api_key or api_key.strip() in ("", "your_pinecone_api_key_here"):
        raise ValueError(
            "PINECONE_API_KEY is not configured in environment settings. "
            "Please provide a valid Pinecone API key."
        )

    try:
        _pinecone_client = Pinecone(api_key=api_key.strip())
        logger.info("Pinecone client initialized successfully.")
        return _pinecone_client
    except Exception as exc:
        logger.error("Failed to initialize Pinecone client: %s", exc)
        raise RuntimeError(f"Could not connect to Pinecone: {str(exc)}") from exc


def get_or_create_index(index_name: str | None = None) -> Any:
    """
    Connects to the specified Pinecone index, creating it if it does not already exist.
    """
    settings = get_settings()
    target_name = index_name or settings.PINECONE_INDEX_NAME or "export-customs-rules"
    pc = get_pinecone_client()

    try:
        existing_indexes = [idx["name"] for idx in pc.list_indexes()]

        if target_name not in existing_indexes:
            logger.info("Index '%s' not found. Creating Pinecone serverless index...", target_name)
            pc.create_index(
                name=target_name,
                dimension=VECTOR_DIMENSION,
                metric=VECTOR_METRIC,
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            logger.info("Successfully created Pinecone index '%s'.", target_name)

        return pc.Index(target_name)
    except Exception as exc:
        logger.warning(
            "Could not connect to remote Pinecone index '%s' (%s). Local fallback will be used.",
            target_name,
            exc,
        )
        return None


def is_local_vector_store_populated() -> bool:
    """Returns True when rules have already been indexed into local store."""
    return len(_LOCAL_VECTOR_STORE) > 0


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
    replace_all: bool = False,
) -> int:
    """
    Upserts vector records to Pinecone index.
    Each record must contain: id, values, and metadata.
    """
    if not records:
        return 0

    settings = get_settings()
    target_namespace = namespace or settings.PINECONE_NAMESPACE or "indian-export-regulations-v1"

    # Keep local fallback store synchronized without dropping existing entries on incremental upserts
    global _LOCAL_VECTOR_STORE
    if replace_all:
        _LOCAL_VECTOR_STORE = records.copy()
    else:
        by_id = {rec["id"]: rec for rec in _LOCAL_VECTOR_STORE}
        for rec in records:
            by_id[rec["id"]] = rec
        _LOCAL_VECTOR_STORE = list(by_id.values())

    try:
        index = get_or_create_index(index_name)
        if index is not None:
            vectors_payload = [
                {
                    "id": r["id"],
                    "values": r["values"],
                    "metadata": r.get("metadata", {}),
                }
                for r in records
            ]
            index.upsert(vectors=vectors_payload, namespace=target_namespace)
            logger.info("Upserted %d rules to Pinecone namespace '%s'.", len(records), target_namespace)
            return len(records)
    except Exception as exc:
        logger.warning("Remote Pinecone upsert failed (%s). Rules stored in local fallback cache.", exc)

    return len(records)


def delete_rules_from_pinecone(
    rule_ids: list[str],
    index_name: str | None = None,
    namespace: str | None = None,
) -> int:
    """Deletes withdrawn or deactivated rule vectors from Pinecone and local cache."""
    if not rule_ids:
        return 0

    settings = get_settings()
    target_namespace = namespace or settings.PINECONE_NAMESPACE or "indian-export-regulations-v1"
    id_set = set(rule_ids)

    global _LOCAL_VECTOR_STORE
    before_count = len(_LOCAL_VECTOR_STORE)
    _LOCAL_VECTOR_STORE = [rec for rec in _LOCAL_VECTOR_STORE if rec.get("id") not in id_set]
    removed_local = before_count - len(_LOCAL_VECTOR_STORE)

    try:
        index = get_or_create_index(index_name)
        if index is not None:
            index.delete(ids=list(id_set), namespace=target_namespace)
            logger.info("Deleted %d withdrawn rules from Pinecone namespace '%s'.", len(id_set), target_namespace)
            return len(id_set)
    except Exception as exc:
        logger.warning("Remote Pinecone delete failed (%s). Removed %d from local fallback cache.", exc, removed_local)

    return max(removed_local, len(id_set))


def query_regulatory_rules(
    query_vector: list[float],
    top_k: int = 3,
    hs_prefix: str | None = None,
    index_name: str | None = None,
    namespace: str | None = None,
) -> list[dict[str, Any]]:
    """
    Semantically queries regulatory rules using cosine similarity and optional HS code filtering.
    """
    settings = get_settings()
    target_namespace = namespace or settings.PINECONE_NAMESPACE or "indian-export-regulations-v1"

    # 1. Try remote Pinecone query
    try:
        index = get_or_create_index(index_name)
        if index is not None:
            metadata_filter = None
            if hs_prefix:
                clean_hs = "".join(filter(str.isdigit, str(hs_prefix)))[:4]
                metadata_filter = {"applicable_hs_prefixes": {"$in": ["ALL", clean_hs, clean_hs[:2]]}}


            kwargs: dict[str, Any] = {
                "vector": query_vector,
                "top_k": top_k,
                "include_metadata": True,
                "namespace": target_namespace,
            }
            if metadata_filter:
                kwargs["filter"] = metadata_filter

            response = index.query(**kwargs)
            matches = []
            for match in response.get("matches", []):
                matches.append(
                    {
                        "rule_id": match["id"],
                        "score": round(float(match["score"]), 4),
                        "metadata": match.get("metadata", {}),
                    }
                )
            if matches:
                return matches
    except Exception as exc:
        logger.warning("Remote Pinecone query failed (%s). Falling back to local vector store.", exc)

    # 2. Local Fallback Cosine Search
    scored_records = []
    clean_hs = "".join(filter(str.isdigit, str(hs_prefix)))[:4] if hs_prefix else None

    for rec in _LOCAL_VECTOR_STORE:
        meta = rec.get("metadata", {})
        if clean_hs:
            allowed_prefixes = meta.get("applicable_hs_prefixes", ["ALL"])
            if "ALL" not in allowed_prefixes and not any(clean_hs.startswith(p) for p in allowed_prefixes):
                continue

        score = _cosine_similarity(query_vector, rec["values"])
        scored_records.append(
            {
                "rule_id": rec["id"],
                "score": round(score, 4),
                "metadata": meta,
            }
        )

    scored_records.sort(key=lambda x: x["score"], reverse=True)
    return scored_records[:top_k]
