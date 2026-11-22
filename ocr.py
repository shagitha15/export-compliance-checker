"""
OCR and Text Extraction Module for Export Customs Documentation Compliance Checker.

Uses PyMuPDF to extract text from PDF files while preserving page-wise structure.
Fully compatible with Python 3.13+.
"""

from __future__ import annotations

import logging
from pathlib import Path

try:
    import pymupdf
except ImportError:
    try:
        import fitz as pymupdf
    except ImportError as err:
        raise ImportError(
            "PyMuPDF is required to extract text from PDF files. "
            "Please install it using 'pip install pymupdf'."
        ) from err

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str | Path) -> dict[int, str]:
    """
    Extracts and preserves page-wise text from a PDF file using PyMuPDF.

    Args:
        pdf_path: Path to the target PDF file (string or Path object).

    Returns:
        dict[int, str]: A dictionary where keys are 1-based page numbers (int)
                        and values are the extracted text for each page (str).

    Raises:
        FileNotFoundError: If the specified PDF file does not exist.
        ValueError: If pdf_path is invalid, points to an empty file (0 bytes),
                    points to a corrupted/non-PDF file, contains 0 pages,
                    or is password-encrypted.
    """
    if not pdf_path:
        raise ValueError("Invalid PDF path: path cannot be empty.")

    file_path = Path(pdf_path)

    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path.resolve()}")

    if not file_path.is_file():
        raise ValueError(f"Path is not a regular file: {file_path.resolve()}")

    # Check for empty file (0 bytes)
    if file_path.stat().st_size == 0:
        raise ValueError(f"PDF file is empty (0 bytes): {file_path.name}")

    page_wise_text: dict[int, str] = {}

    try:
        with pymupdf.open(file_path) as doc:
            # Check for encryption
            if doc.is_encrypted:
                if not doc.authenticate(""):
                    raise ValueError(
                        f"PDF file is password-protected or encrypted: {file_path.name}"
                    )

            # Check for empty document (0 pages)
            if doc.page_count == 0:
                raise ValueError(f"PDF document contains 0 pages: {file_path.name}")

            # Read all pages and preserve page-wise text
            for page_number, page in enumerate(doc, start=1):
                text = page.get_text() or ""
                page_wise_text[page_number] = text

    except pymupdf.FileDataError as exc:
        raise ValueError(f"Invalid or corrupted PDF file ({file_path.name}): {exc}") from exc
    except pymupdf.EmptyFileError as exc:
        raise ValueError(f"PDF file is empty ({file_path.name}): {exc}") from exc
    except Exception as exc:
        if isinstance(exc, (ValueError, FileNotFoundError)):
            raise
        raise ValueError(f"Failed to extract text from PDF ({file_path.name}): {exc}") from exc

    # Log advisory warning if no text was found across all pages (e.g. scanned image)
    total_characters = sum(len(content.strip()) for content in page_wise_text.values())
    if total_characters == 0:
        logger.warning(
            "Extracted 0 characters across %d page(s) from '%s'. "
            "Document may be a scanned image without an embedded text layer.",
            len(page_wise_text),
            file_path.name,
        )

    return page_wise_text


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ocr.py <path_to_pdf>")
        sys.exit(1)

    target_pdf = sys.argv[1]
    try:
        extracted = extract_text_from_pdf(target_pdf)
        print(f"Successfully extracted text from {len(extracted)} page(s):\n")
        for page_num, page_content in extracted.items():
            print(f"--- Page {page_num} ({len(page_content)} characters) ---")
            print(page_content[:200] + ("..." if len(page_content) > 200 else ""))
            print()
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
