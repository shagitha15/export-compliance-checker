"""
Seeder Module to Ingest, Embed, and Index Official Indian Export Customs Regulations.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from services.rules.embedding_service import generate_embedding
from services.rules.pinecone_service import upsert_rules_to_pinecone

logger = logging.getLogger(__name__)

RULES_DATA_FILE = Path("data") / "rules" / "indian_export_regulations.json"


def load_seed_rules() -> list[dict[str, Any]]:
    """Loads statutory export rules from the structured JSON dataset."""
    if not RULES_DATA_FILE.is_file():
        raise FileNotFoundError(f"Rules seed dataset not found at: {RULES_DATA_FILE.resolve()}")

    with RULES_DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def prepare_rule_text_for_embedding(rule: dict[str, Any]) -> str:
    """Combines rule ancestry and content for semantic embedding generation."""
    return (
        f"AUTHORITY: {rule.get('authority')}\n"
        f"POLICY: {rule.get('policy_document')} ({rule.get('section_or_para')})\n"
        f"TITLE: {rule.get('rule_title')}\n"
        f"CATEGORY: {rule.get('category')}\n"
        f"CONTENT: {rule.get('text')}"
    )


def seed_regulatory_rules() -> int:
    """
    Reads regulatory rules, generates 768-dim embeddings using text-embedding-004,
    and indexes them into Pinecone (and in-memory fallback).

    Returns:
        int: Number of statutory rules indexed.
    """
    rules = load_seed_rules()
    logger.info("Loaded %d statutory export rules from %s", len(rules), RULES_DATA_FILE)

    records = []
    for rule in rules:
        rule_id = rule["rule_id"]
        embed_text = prepare_rule_text_for_embedding(rule)
        vector = generate_embedding(embed_text, task_type="RETRIEVAL_DOCUMENT")

        # Metadata to persist alongside vector
        metadata = {
            "rule_id": rule_id,
            "authority": rule.get("authority", ""),
            "category": rule.get("category", ""),
            "policy_document": rule.get("policy_document", ""),
            "section_or_para": rule.get("section_or_para", ""),
            "rule_title": rule.get("rule_title", ""),
            "applicable_hs_prefixes": rule.get("applicable_hs_prefixes", ["ALL"]),
            "mandatory_documents": rule.get("mandatory_documents", []),
            "prohibited_or_restricted": rule.get("prohibited_or_restricted", False),
            "requires_license": rule.get("requires_license", False),
            "source_url": rule.get("source_url", ""),
            "text": rule.get("text", ""),
        }

        records.append(
            {
                "id": rule_id,
                "values": vector,
                "metadata": metadata,
            }
        )

    count = upsert_rules_to_pinecone(records)
    logger.info("Successfully seeded and indexed %d rules.", count)
    return count


if __name__ == "__main__":
    import sys

    print("--- Seeding Indian Export Customs Regulations to Pinecone ---")
    try:
        total = seed_regulatory_rules()
        print(f"✓ Successfully indexed {total} statutory export rules.")
    except Exception as e:
        print(f"✗ Seeding failed: {e}", file=sys.stderr)
