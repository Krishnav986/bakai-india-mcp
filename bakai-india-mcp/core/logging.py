"""Structured and safe logging for BAKAI India MCP Server.

Ensures all log lines route to sys.stderr (preserving stdout exclusively
for JSON-RPC MCP messages) and redacts API keys and sensitive tokens.
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any
from core.config import settings

# Patterns for sensitive tokens to mask
_SECRET_PATTERNS = [
    re.compile(r"(api[-_]?key\s*[=:]\s*['\"]?)([\w\-]{8,})(['\"]?)", re.IGNORECASE),
    re.compile(r"(token\s*[=:]\s*['\"]?)([\w\-]{8,})(['\"]?)", re.IGNORECASE),
    re.compile(r"(secret\s*[=:]\s*['\"]?)([\w\-]{8,})(['\"]?)", re.IGNORECASE),
    re.compile(r"(bearer\s+)([\w\-\.]{12,})", re.IGNORECASE),
]


class RedactingFormatter(logging.Formatter):
    """Custom formatter that masks sensitive keys and credentials."""

    def format(self, record: logging.LogRecord) -> str:
        orig = super().format(record)
        redacted = orig
        for pattern in _SECRET_PATTERNS:
            redacted = pattern.sub(r"\1***REDACTED***\3" if pattern.groups == 3 else r"\1***REDACTED***", redacted)
        return redacted


def setup_logger(name: str = "bakai_mcp") -> logging.Logger:
    """Configures and returns a logger with stderr handler and redacting formatter."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(stream=sys.stderr)
        formatter = RedactingFormatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))
        logger.propagate = False
    return logger


logger = setup_logger()
