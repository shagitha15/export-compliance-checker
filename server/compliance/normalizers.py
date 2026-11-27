"""
Normalization and canonicalization utilities for customs cross-document validation.
"""

from __future__ import annotations

import re
from typing import Any

# Standard corporate suffixes to strip during entity name matching
CORPORATE_SUFFIXES = {
    "ltd", "limited", "inc", "incorporated", "corp", "corporation",
    "co", "company", "llc", "pvt", "private", "gmbh", "sa", "plc",
    "ag", "bv", "srl", "sl", "pty"
}

# Unit conversion factors to standard Kilograms (KG)
WEIGHT_TO_KG_FACTORS = {
    "kg": 1.0,
    "kgs": 1.0,
    "kilogram": 1.0,
    "kilograms": 1.0,
    "g": 0.001,
    "grams": 0.001,
    "gm": 0.001,
    "lb": 0.45359237,
    "lbs": 0.45359237,
    "pound": 0.45359237,
    "pounds": 0.45359237,
    "mt": 1000.0,
    "metric ton": 1000.0,
    "ton": 1000.0,
    "tons": 1000.0,
}


def clean_string(value: Any) -> str:
    """Strips whitespace, replaces multiple spaces, and handles None."""
    if value is None:
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)


def normalize_identifier(value: Any) -> str:
    """Normalizes codes, numbers, and IDs (e.g. invoice numbers, tax IDs)."""
    if not value:
        return ""
    # Strip spaces, hyphens, and slashes for loose comparison while keeping alphanumerics
    cleaned = clean_string(value).upper()
    return re.sub(r"[\s\-_/.]+", "", cleaned)


def normalize_company_name(name: Any) -> set[str]:
    """Tokenizes and normalizes a company name, removing corporate suffixes."""
    if not name:
        return set()
    cleaned = clean_string(name).lower()
    # Strip non-alphanumeric characters
    tokens = re.findall(r"[a-z0-9]+", cleaned)
    filtered = {t for t in tokens if t not in CORPORATE_SUFFIXES and len(t) > 1}
    return filtered


def company_names_match(name1: Any, name2: Any, threshold: float = 0.75) -> bool:
    """
    Evaluates whether two company names match using Jaccard token overlap.
    A threshold of 0.75 allows for slight legal name phrasing differences.
    """
    tokens1 = normalize_company_name(name1)
    tokens2 = normalize_company_name(name2)

    if not tokens1 or not tokens2:
        return False

    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)

    jaccard_similarity = len(intersection) / len(union)
    if jaccard_similarity >= threshold:
        return True

    # Check if one set is a subset of the other (e.g., "Acme Electronics" in "Acme Electronics International")
    if tokens1.issubset(tokens2) or tokens2.issubset(tokens1):
        if len(intersection) >= min(len(tokens1), len(tokens2)):
            return True

    return False


def normalize_hs_code(hs_code: Any) -> str:
    """
    Extracts the standard 6-digit Harmonized System subheading.
    Strips dots, spaces, and trailing national digits.
    """
    if not hs_code:
        return ""
    digits = re.sub(r"\D", "", str(hs_code))
    # Return first 6 digits if available, otherwise available digits
    return digits[:6] if len(digits) >= 6 else digits


def normalize_currency(currency: Any) -> str:
    """Normalizes currency to uppercase 3-letter ISO code."""
    if not currency:
        return ""
    cleaned = clean_string(currency).upper()
    # Common mappings
    mapping = {
        "$": "USD",
        "US$": "USD",
        "€": "EUR",
        "£": "GBP",
        "₹": "INR",
        "RS": "INR",
        "INR": "INR",
        "USD": "USD",
        "EUR": "EUR",
    }
    return mapping.get(cleaned, cleaned[:3])


def normalize_weight_to_kg(weight_value: Any, unit: Any = None) -> float | None:
    """Normalizes weight to Kilograms (KG)."""
    if weight_value is None:
        return None
    try:
        val = float(str(weight_value).replace(",", ""))
    except (ValueError, TypeError):
        return None

    if not unit:
        return round(val, 3)

    unit_clean = clean_string(unit).lower()
    factor = WEIGHT_TO_KG_FACTORS.get(unit_clean, 1.0)
    return round(val * factor, 3)


def parse_numeric(value: Any) -> float | None:
    """Extracts a float number safely from strings or numbers."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace(",", "").strip()
    match = re.search(r"[-+]?\d*\.?\d+", cleaned)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None
