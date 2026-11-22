"""
Centralized Structured Logging Configuration.
"""

import logging
import sys
from server.config.settings import get_settings


def setup_logging() -> logging.Logger:
    settings = get_settings()
    log_level = getattr(logging, settings.SERVER_LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    log = logging.getLogger("customs_compliance")
    log.setLevel(log_level)
    return log


logger = setup_logging()


def get_logger(name: str = "customs_compliance") -> logging.Logger:
    """
    Get a named logger instance adhering to centralized format.
    """
    return logging.getLogger(name)


__all__ = ["logger", "get_logger", "setup_logging"]

