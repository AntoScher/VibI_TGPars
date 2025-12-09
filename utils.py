"""
Helper utilities for the Deepseek CLI.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, List

logger = logging.getLogger("deepseek-cli")

DEFAULT_CHUNK_SIZE = 4000  # chars per chunk for safety
HARD_LIMIT_CHARS = 16000   # warn if above


def read_text_from_file(path: str) -> str:
    """Read text content from a file path."""
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    text = file_path.read_text(encoding="utf-8")
    logger.info("Read %d characters from %s", len(text), path)
    return text


def chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> List[str]:
    """
    Split text into roughly chunk_size character segments, preserving order.
    """
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def warn_if_too_long(text: str) -> None:
    """Log a warning if text length exceeds a hard threshold."""
    if len(text) > HARD_LIMIT_CHARS:
        logger.warning(
            "Input is large (%d chars). It will be processed in chunks; "
            "consider shortening the input for better summaries.",
            len(text),
        )

