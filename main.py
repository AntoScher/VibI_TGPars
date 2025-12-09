"""
CLI tool for summarizing text via Deepseek API.

Usage examples:
  python main.py summary --file messages.txt
  python main.py summary --text "любой текст" --max-tokens 256 --json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any, Dict

from deepseek import DeepseekError, generate_summary
from utils import (
    DEFAULT_CHUNK_SIZE,
    chunk_text,
    read_text_from_file,
    warn_if_too_long,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("deepseek-cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deepseek summarization CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    summary_parser = subparsers.add_parser("summary", help="Create a summary")
    summary_parser.add_argument(
        "--file", type=str, help="Path to a text file with messages"
    )
    summary_parser.add_argument(
        "--text", type=str, help="Text to summarize (takes priority over --file)"
    )
    summary_parser.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        help="Max tokens for the model response (default: 512)",
    )
    summary_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON",
    )
    return parser


def summarize_text(text: str, *, max_tokens: int) -> str:
    """
    Handle long texts by chunking and summarizing progressively.
    """
    warn_if_too_long(text)

    CHUNK_LIMIT = DEFAULT_CHUNK_SIZE
    if len(text) <= CHUNK_LIMIT:
        return generate_summary(text, max_tokens=max_tokens)

    # Chunk the text and summarize each part, then summarize the combined summaries.
    chunks = chunk_text(text, chunk_size=CHUNK_LIMIT)
    logger.info("Text will be processed in %d chunks", len(chunks))
    partial_summaries = []
    for idx, chunk in enumerate(chunks, start=1):
        logger.info("Summarizing chunk %d/%d (%d chars)", idx, len(chunks), len(chunk))
        partial = generate_summary(chunk, max_tokens=max_tokens)
        partial_summaries.append(partial)

    combined = "\n\n".join(partial_summaries)
    logger.info("Summarizing combined %d partial summaries", len(partial_summaries))
    final_summary = generate_summary(combined, max_tokens=max_tokens)
    return final_summary


def handle_summary(args: argparse.Namespace) -> int:
    text: str | None = None

    if args.text:
        text = args.text
    elif args.file:
        try:
            text = read_text_from_file(args.file)
        except FileNotFoundError as exc:
            logger.error(str(exc))
            return 1
    else:
        logger.error("Please provide --text or --file")
        return 1

    try:
        summary = summarize_text(text, max_tokens=args.max_tokens)
    except DeepseekError as exc:
        logger.error(str(exc))
        return 1

    if args.json:
        output: Dict[str, Any] = {"summary": summary}
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(summary)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "summary":
        return handle_summary(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

