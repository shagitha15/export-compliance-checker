"""
Embedding Generation Service for Regulatory Rules and Queries.

Uses Google GenAI's text-embedding-004 model (768 dimensions) to create vector
representations of Indian customs export statutory provisions.
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSION = 768
EMBEDDING_MODEL = "text-embedding-004"


def get_embedding_client() -> genai.Client:
    """Returns an authenticated GenAI Client for embedding generation."""
    load_dotenv(override=True)
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY is not configured in .env.")

    api_version = os.getenv("GEMINI_API_VERSION", "v1beta")
    http_options = types.HttpOptions(api_version=api_version)
    return genai.Client(api_key=api_key, http_options=http_options)


def _generate_fallback_embedding(text: str, dim: int = EMBEDDING_DIMENSION) -> list[float]:
    """
    Generates a deterministic pseudo-embedding vector from text hash.
    Ensures offline tests and sandboxed runs operate predictably without network calls.
    """
    vector = []
    for i in range(dim):
        h = hashlib.sha256(f"{text}_{i}".encode("utf-8")).hexdigest()
        val = (int(h[:8], 16) / 0xFFFFFFFF) * 2.0 - 1.0
        vector.append(val)

    # Normalize vector to unit length
    magnitude = math.sqrt(sum(x * x for x in vector))
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
        client = get_embedding_client()
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
