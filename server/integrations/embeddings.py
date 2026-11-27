"""
Embedding Generation Integration for Regulatory Rules and Queries.
Uses Google GenAI text-embedding-004 model (768 dimensions) with deterministic fallback.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any
from google.genai import types
from server.config.settings import get_settings
from server.integrations.gemini import get_gemini_client
from server.logging.logger import get_logger

logger = get_logger("server.integrations.embeddings")

EMBEDDING_DIMENSION = 768
EMBEDDING_MODEL = "text-embedding-004"


def _generate_fallback_embedding(text: str, dim: int = EMBEDDING_DIMENSION) -> list[float]:
    """
    Generates a deterministic pseudo-embedding vector from SHA-256 text hash.
    Ensures offline tests and sandboxed runs operate predictably without network calls.
    """
    vector = []
    for i in range(dim):
        h = hashlib.sha256(f"{text}_{i}".encode("utf-8")).hexdigest()
        val = (int(h[:8], 16) / 0xFFFFFFFF) * 2.0 - 1.0
        vector.append(val)

    # Normalize vector to unit length
    magnitude = math.sqrt(sum(x * x for x in vector))
    if magnitude == 0:
        return [0.0] * dim
    return [round(x / magnitude, 6) for x in vector]


def generate_embedding(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    """
    Generates a 768-dimensional embedding vector for the given text.

    Args:
        text: Statutory text or query string.
        task_type: 'RETRIEVAL_DOCUMENT' (for indexing) or 'RETRIEVAL_QUERY' (for search).

    Returns:
        list[float]: 768-dimensional float embedding vector.
    """
    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIMENSION

    cleaned_text = text.strip()

    try:
        client = get_gemini_client()
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=cleaned_text,
        )
        if hasattr(response, "embedding") and hasattr(response.embedding, "values"):
            return list(response.embedding.values)
        if hasattr(response, "embeddings") and response.embeddings:
            return list(response.embeddings[0].values)
    except Exception as exc:
        logger.warning(
            "Google GenAI embedding generation failed (%s). Using deterministic fallback embedding.",
            exc,
        )

    return _generate_fallback_embedding(cleaned_text, dim=EMBEDDING_DIMENSION)


def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generates embeddings for a batch of strings."""
    return [generate_embedding(t) for t in texts]
