"""
Document Intelligence Structured Extraction Engine.
Uses Gemini with JSON response mode, exponential-backoff retries on transient errors,
configurable timeouts, model capability checks, and non-silent PyMuPDF text fallback.
"""

from __future__ import annotations

import concurrent.futures
import json
import re
import time
from pathlib import Path
from typing import Any

from google.genai import errors, types

from server.config.settings import get_settings
from server.document_intelligence.fallback_extractor import extract_structured_fallback
from server.document_intelligence.prompts import build_extraction_prompt, format_extracted_text
from server.document_intelligence.schemas import DOCUMENT_SCHEMAS
from server.integrations.gemini import (
    UnsupportedGeminiModelError,
    get_gemini_client,
    validate_gemini_model,
)
from server.logging.logger import get_logger

logger = get_logger("server.document_intelligence")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EXTRACTED_DATA_DIR = PROJECT_ROOT / "extracted_data"
EXTRACTED_DATA_DIR.mkdir(parents=True, exist_ok=True)

MAX_ALLOWED_RETRIES = 3
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}


class GeminiExtractionError(RuntimeError):
    """Structured error raised when Gemini extraction fails and cannot fall back."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "GEMINI_EXTRACTION_FAILED",
        status_code: int | None = None,
        attempts: int = 1,
        model_name: str = "",
        retried: bool = False,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code
        self.attempts = attempts
        self.model_name = model_name
        self.retried = retried

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "status_code": self.status_code,
            "attempts": self.attempts,
            "model_name": self.model_name,
            "retried": self.retried,
            "message": str(self),
        }


def _extract_status_code(exc: Exception) -> int | None:
    """Extracts an HTTP status code from APIError or exception text if present."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if isinstance(code, int):
        return code
    match = re.search(r"\b(429|5\d{2}|4\d{2})\b", str(exc))
    return int(match.group(1)) if match else None


def _is_transient_gemini_error(exc: Exception) -> bool:
    """Determines whether a Gemini API / transport error is transient and retryable."""
    if isinstance(exc, (UnsupportedGeminiModelError, ValueError)):
        return False

    if isinstance(exc, (TimeoutError, concurrent.futures.TimeoutError, ConnectionError)):
        return True

    status_code = _extract_status_code(exc)
    if status_code is not None:
        return status_code == 429 or 500 <= status_code < 600

    msg = str(exc).lower()
    transient_markers = (
        "high demand",
        "temporarily unavailable",
        "unavailable",
        "resource_exhausted",
        "rate limit",
        "too many requests",
        "timed out",
        "timeout",
        "connection reset",
    )
    return any(marker in msg for marker in transient_markers)


def _call_generate_with_timeout(
    client: Any,
    model_name: str,
    prompt: str,
    config: types.GenerateContentConfig,
    timeout_seconds: float,
) -> Any:
    """Executes client.models.generate_content guarded by an explicit wall-clock timeout."""
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(
        client.models.generate_content,
        model=model_name,
        contents=prompt,
        config=config,
    )
    try:
        return future.result(timeout=timeout_seconds)
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        raise TimeoutError(
            f"Gemini API request exceeded configured timeout of {timeout_seconds:.1f}s"
        ) from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _parse_gemini_json_response(response: Any, document_type: str) -> dict[str, Any]:
    """Parses and sanitizes Gemini response text into a JSON dictionary."""
    response_text = getattr(response, "text", None) or ""
    if not response_text.strip():
        raise RuntimeError(f"Gemini API returned an empty response for {document_type}.")

    clean_json_str = response_text.strip()
    if clean_json_str.startswith("```"):
        clean_json_str = re.sub(r"^```(?:json)?\s*", "", clean_json_str)
        clean_json_str = re.sub(r"\s*```$", "", clean_json_str)

    parsed = json.loads(clean_json_str)
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Gemini API returned non-object JSON ({type(parsed).__name__}).")
    return parsed


def _persist_extracted_json(extracted_json: dict[str, Any], source_filename: str) -> None:
    """Persists extracted JSON payload to extracted_data/ directory."""
    stem = Path(source_filename).stem
    output_file = EXTRACTED_DATA_DIR / f"{stem}_extracted.json"
    try:
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(extracted_json, f, indent=2, ensure_ascii=False)
        logger.info("Saved extracted JSON to %s", output_file)
    except Exception as exc:
        logger.warning("Could not persist extracted JSON to %s: %s", output_file, exc)


def extract_document_data(
    document_type: str,
    pdf_text: dict[int, str] | str,
    source_filename: str | None = None,
    save_to_disk: bool = True,
    *,
    pdf_bytes: bytes | None = None,
    timeout_seconds: float | None = None,
    max_retries: int | None = None,
    retry_base_delay: float | None = None,
    allow_fallback: bool | None = None,
) -> dict[str, Any]:
    """
    Extracts structured JSON data from export customs document text (or scanned PDF bytes)
    using Gemini, with model capability validation, configurable timeout, exponential-backoff
    retries (max 3), and non-silent PyMuPDF text fallback.
    """
    if document_type not in DOCUMENT_SCHEMAS:
        raise ValueError(
            f"Unsupported document type '{document_type}'. "
            f"Allowed types: {list(DOCUMENT_SCHEMAS.keys())}"
        )

    formatted_text = format_extracted_text(pdf_text)
    if not formatted_text and not pdf_bytes:
        raise ValueError(
            "Extracted text is empty. Cannot extract structured data from an empty document."
        )

    settings = get_settings()
    model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"
    effective_timeout = (
        float(timeout_seconds)
        if timeout_seconds is not None
        else float(getattr(settings, "GEMINI_TIMEOUT_SECONDS", 30.0))
    )
    configured_retries = (
        int(max_retries)
        if max_retries is not None
        else int(getattr(settings, "GEMINI_MAX_RETRIES", MAX_ALLOWED_RETRIES))
    )
    effective_retries = max(0, min(MAX_ALLOWED_RETRIES, configured_retries))
    base_delay = (
        float(retry_base_delay)
        if retry_base_delay is not None
        else float(getattr(settings, "GEMINI_RETRY_BASE_DELAY_SECONDS", 1.0))
    )
    use_fallback = (
        bool(allow_fallback)
        if allow_fallback is not None
        else bool(getattr(settings, "GEMINI_ENABLE_PYMUPDF_FALLBACK", True))
    )

    target_schema = DOCUMENT_SCHEMAS[document_type]
    if formatted_text:
        contents: Any = build_extraction_prompt(document_type, formatted_text, target_schema)
    else:
        # Scanned PDF without embedded text layer: send raw PDF bytes + schema prompt to Gemini
        scan_prompt = build_extraction_prompt(
            document_type,
            "[Scanned PDF attached as binary document — perform OCR and extract fields directly from the pages.]",
            target_schema,
        )
        contents = [
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            scan_prompt,
        ]

    last_error: GeminiExtractionError | None = None
    attempts_made = 0

    try:
        client = get_gemini_client(timeout_seconds=effective_timeout)
        model_caps = validate_gemini_model(model_name, client=client)

        config_kwargs: dict[str, Any] = {"temperature": 0.0}
        if model_caps.get("supports_json_mode", True):
            config_kwargs["response_mime_type"] = "application/json"
        config = types.GenerateContentConfig(**config_kwargs)

        total_attempts = 1 + effective_retries
        for attempt_idx in range(total_attempts):
            attempts_made = attempt_idx + 1
            try:
                response = _call_generate_with_timeout(
                    client=client,
                    model_name=model_name,
                    prompt=contents,
                    config=config,
                    timeout_seconds=effective_timeout,
                )
                extracted_json = _parse_gemini_json_response(response, document_type)
                if save_to_disk and source_filename:
                    _persist_extracted_json(extracted_json, source_filename)
                return extracted_json

            except json.JSONDecodeError as exc:
                logger.error("Failed to parse Gemini response as JSON: %s", exc)
                last_error = GeminiExtractionError(
                    f"Failed to parse Gemini model response as valid JSON: {exc}",
                    error_code="GEMINI_INVALID_JSON",
                    attempts=attempts_made,
                    model_name=model_name,
                    retried=attempt_idx > 0,
                )
                break

            except Exception as exc:
                status_code = _extract_status_code(exc)
                transient = _is_transient_gemini_error(exc)
                err_msg = (
                    f"Gemini API error [{status_code}]: {getattr(exc, 'message', None) or str(exc)}"
                    if status_code is not None
                    else f"Gemini API extraction failed: {str(exc)}"
                )

                if transient and attempt_idx < effective_retries:
                    delay = max(0.0, base_delay * (2 ** attempt_idx))
                    logger.warning(
                        "Transient Gemini failure on attempt %d/%d for %s (%s). Retrying in %.2fs...",
                        attempts_made,
                        total_attempts,
                        document_type,
                        err_msg,
                        delay,
                    )
                    if delay > 0:
                        time.sleep(delay)
                    continue

                err_code = (
                    "GEMINI_TIMEOUT"
                    if isinstance(exc, TimeoutError)
                    else ("GEMINI_SERVICE_UNAVAILABLE" if status_code in TRANSIENT_STATUS_CODES else "GEMINI_API_ERROR")
                )
                logger.error(
                    "Gemini extraction failed after %d attempt(s) for %s: %s",
                    attempts_made,
                    document_type,
                    err_msg,
                )
                last_error = GeminiExtractionError(
                    f"{err_msg} (after {attempts_made} attempt(s))",
                    error_code=err_code,
                    status_code=status_code,
                    attempts=attempts_made,
                    model_name=model_name,
                    retried=attempts_made > 1,
                )
                break

    except UnsupportedGeminiModelError as exc:
        logger.error("Unsupported Gemini model configuration: %s", exc)
        last_error = GeminiExtractionError(
            str(exc),
            error_code="GEMINI_UNSUPPORTED_MODEL",
            attempts=attempts_made,
            model_name=model_name,
            retried=False,
        )
    except ValueError as exc:
        # Missing API key or invalid configuration can still trigger fallback if allowed
        logger.error("Gemini configuration error: %s", exc)
        last_error = GeminiExtractionError(
            str(exc),
            error_code="GEMINI_CONFIG_ERROR",
            attempts=attempts_made,
            model_name=model_name,
            retried=False,
        )
    except Exception as exc:
        logger.error("Unexpected Gemini client initialization error: %s", exc)
        last_error = GeminiExtractionError(
            f"Gemini API extraction failed: {str(exc)}",
            error_code="GEMINI_CLIENT_ERROR",
            attempts=attempts_made,
            model_name=model_name,
            retried=False,
        )

    assert last_error is not None

    # Attempt deterministic PyMuPDF-text fallback without marking it as AI success
    if use_fallback:
        fallback_data, populated_count = extract_structured_fallback(document_type, pdf_text)
        if populated_count > 0:
            logger.warning(
                "Gemini AI extraction failed (%s). Using deterministic PyMuPDF fallback extraction "
                "for '%s' (%d field(s) extracted; NOT marked as AI success).",
                last_error,
                document_type,
                populated_count,
            )
            fallback_data["_extraction_metadata"] = {
                "source": "pymupdf_fallback",
                "ai_extraction_succeeded": False,
                "fallback_used": True,
                "populated_fields": populated_count,
                "gemini_error": str(last_error),
                "gemini_error_code": last_error.error_code,
                "gemini_status_code": last_error.status_code,
                "attempts": last_error.attempts,
            }
            if save_to_disk and source_filename:
                _persist_extracted_json(fallback_data, source_filename)
            return fallback_data

    raise last_error
