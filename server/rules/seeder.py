"""
Seeder Module to Ingest, Embed, and Index Official Indian Export Customs Regulations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from server.integrations.embeddings import generate_embedding
from server.integrations.pinecone import is_local_vector_store_populated, upsert_rules_to_pinecone
from server.logging.logger import get_logger

_RULES_SEEDED = False

logger = get_logger("server.rules.seeder")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RULES_DATA_FILE = PROJECT_ROOT / "data" / "rules" / "indian_export_regulations.json"


def load_seed_rules() -> list[dict[str, Any]]:
    """
    Loads active verified regulatory rules from RuleRegistryRepository (live synced + seed baseline),
    falling back safely to the immutable static JSON file if needed.
    """
    try:
        from server.repositories.rules_repository import RuleRegistryRepository

        active_rules = RuleRegistryRepository().list_active_verified_rules()
        if active_rules:
            return [
                {
                    "rule_id": r.rule_id,
                    "authority": r.authority,
                    "category": r.source,
                    "policy_document": r.policy_document,
                    "section_or_para": r.para_ref,
                    "rule_title": r.rule_title,
                    "applicable_hs_prefixes": r.applicable_hs_prefixes,
                    "mandatory_documents": r.mandatory_documents,
                    "prohibited_or_restricted": r.severity == "HIGH",
                    "requires_license": any("license" in d.lower() or "scomet" in d.lower() for d in r.mandatory_documents),
                    "source_url": r.source_url,
                    "text": r.rule_text,
                    "effective_date": r.effective_date or "",
                    "published_date": r.published_date or "",
                    "notification_number": r.notification_number,
                    "is_active": True,
                }
                for r in active_rules
            ]
    except Exception as exc:
        logger.warning("Failed loading active rules from repository (%s); falling back to static JSON seed.", exc)

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

    global _RULES_SEEDED
    count = upsert_rules_to_pinecone(records)
    _RULES_SEEDED = count > 0
    logger.info("Successfully seeded and indexed %d rules.", count)
    return count


def ensure_regulatory_rules_seeded() -> int:
    """Seeds regulatory rules once per process unless the local vector cache is empty."""
    if _RULES_SEEDED and is_local_vector_store_populated():
        return 0
    return seed_regulatory_rules()
