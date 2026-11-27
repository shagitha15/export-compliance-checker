"""
Google GenAI (Gemini) Client Integration.
Enforces lazy initialization, configurable request timeouts, and model capability verification.
"""

from __future__ import annotations

from typing import Any
from google import genai
from google.genai import errors, types
from server.config.settings import get_settings
from server.logging.logger import get_logger

logger = get_logger("server.integrations.gemini")

# Cached singleton client instance (for default settings)
_gemini_client: genai.Client | None = None

_UNSUPPORTED_MODEL_PREFIXES = (
    "text-embedding",
    "embedding",
    "imagen",
    "veo",
    "aqa",
    "chirp",
    "lyria",
)


class UnsupportedGeminiModelError(ValueError):
    """Raised when the configured Gemini model does not support structured content extraction."""


def get_gemini_client(
    force_new: bool = False,
    timeout_seconds: float | None = None,
) -> genai.Client:
    """
    Initializes and returns an authenticated GenAI Client configured with v1beta
    and configurable HTTP timeout.
    """
    global _gemini_client

    if _gemini_client is not None and not force_new and timeout_seconds is None:
        return _gemini_client

    settings = get_settings()

    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key.strip() in ("", "your_gemini_api_key_here"):
        raise ValueError(
            "GEMINI_API_KEY is not configured in environment settings. "
            "Please configure a valid Gemini API key."
        )

    api_version = settings.GEMINI_API_VERSION or "v1beta"
    effective_timeout = (
        float(timeout_seconds)
        if timeout_seconds is not None
        else float(getattr(settings, "GEMINI_TIMEOUT_SECONDS", 30.0))
    )
    timeout_ms = max(1000, int(effective_timeout * 1000))
    http_options = types.HttpOptions(api_version=api_version, timeout=timeout_ms)

    try:
        client = genai.Client(api_key=api_key.strip(), http_options=http_options)
        if timeout_seconds is None:
            _gemini_client = client
        logger.info(
            "Gemini GenAI client initialized (api_version=%s, timeout_ms=%d)",
            api_version,
            timeout_ms,
        )
        return client
    except Exception as exc:
        logger.error("Failed to initialize Gemini client: %s", exc)
        raise RuntimeError(f"Could not initialize Gemini GenAI client: {str(exc)}") from exc


def validate_gemini_model(
    model_name: str,
    client: genai.Client | None = None,
) -> dict[str, Any]:
    """
    Verifies whether the configured Gemini model supports generateContent JSON extraction.

    Performs static model-family validation and, when a client is supplied, queries
    model metadata via client.models.get if available (failing open on transient errors
    so the retry pipeline can handle temporary outages, and failing fast on 400/404 or
    explicitly unsupported actions).
    """
    if not model_name or not isinstance(model_name, str) or not model_name.strip():
        raise UnsupportedGeminiModelError("GEMINI_MODEL is empty or invalid.")

    normalized = model_name.strip()
    bare = normalized.removeprefix("models/").lower()

    if any(bare.startswith(prefix) for prefix in _UNSUPPORTED_MODEL_PREFIXES) or "embedding" in bare:
        raise UnsupportedGeminiModelError(
            f"Configured model '{normalized}' is not a generative text/JSON extraction model."
        )

    if not bare.startswith(("gemini", "gemma", "learnlm")):
        raise UnsupportedGeminiModelError(
            f"Configured model '{normalized}' does not appear to be a supported Gemini generative model."
        )

    # Legacy 1.0 text-only models do not support response_mime_type='application/json'
    supports_json_mode = bare not in ("gemini-pro", "gemini-1.0-pro", "gemini-1.0-pro-001")

    if client is not None and hasattr(client, "models") and hasattr(client.models, "get"):
        try:
            model_info = client.models.get(model=normalized)
            actions = (
                getattr(model_info, "supported_actions", None)
                or getattr(model_info, "supported_generation_methods", None)
            )
            if isinstance(actions, (list, tuple, set)) and len(actions) > 0:
                lowered = {str(a).lower() for a in actions}
                if "generatecontent" not in lowered and "generate_content" not in lowered:
                    raise UnsupportedGeminiModelError(
                        f"Model '{normalized}' does not support generateContent (supported_actions={list(actions)})."
                    )
        except UnsupportedGeminiModelError:
            raise
        except errors.APIError as api_err:
            if getattr(api_err, "code", None) in (400, 404):
                raise UnsupportedGeminiModelError(
                    f"Configured Gemini model '{normalized}' was rejected by API ({api_err.code}): {api_err.message}"
                ) from api_err
            logger.debug(
                "Skipping model metadata check for '%s' due to transient API error: %s",
                normalized,
                api_err,
            )
        except Exception as exc:
            logger.debug("Model metadata inspection unavailable for '%s': %s", normalized, exc)

    return {
        "model_name": normalized,
        "supports_generate_content": True,
        "supports_json_mode": supports_json_mode,
    }
