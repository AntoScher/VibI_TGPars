"""
Deepseek API client.
Uses synchronous requests to call /chat/completions for summarization.
"""
from __future__ import annotations

import os
from typing import Any, Dict

import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://api.deepseek.com"
COMPLETIONS_PATH = "/chat/completions"
MODEL_NAME = "deepseek-chat"


class DeepseekError(Exception):
    """Custom error for Deepseek API issues."""


def _get_api_key() -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise DeepseekError("DEEPSEEK_API_KEY not set. Add it to your .env file.")
    return api_key


def generate_summary(text: str, *, max_tokens: int = 512) -> str:
    """
    Call Deepseek chat/completions to generate a summary for the provided text.
    Raises DeepseekError on failures.
    """
    api_key = _get_api_key()
    url = f"{API_BASE}{COMPLETIONS_PATH}"
    payload: Dict[str, Any] = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты – ассистент, который делает краткие выжимки текста. "
                    "Суммаризируй следующий текст на русском языке."
                ),
            },
            {"role": "user", "content": text},
        ],
        "stream": False,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
    except requests.RequestException as exc:
        raise DeepseekError(f"Network error while calling Deepseek: {exc}") from exc

    if response.status_code != 200:
        raise DeepseekError(
            f"Deepseek API returned {response.status_code}: {response.text}"
        )

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise DeepseekError(f"Unexpected response format: {data}") from exc

