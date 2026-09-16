"""
LeakHunter V3 - Telegram Message Parser
Parses scraped Telegram messages, extracts record count estimations, and formats
structured event payloads for ingestion into the LeakHunter event bus and pipeline.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Multiplier lookup for number suffix abbreviations
_MULTIPLIERS = {
    "k": 1_000,
    "thousand": 1_000,
    "m": 1_000_000,
    "million": 1_000_000,
    "millions": 1_000_000,
    "mn": 1_000_000,
    "b": 1_000_000_000,
    "billion": 1_000_000_000,
    "billions": 1_000_000_000,
    "bn": 1_000_000_000,
}

# Regex for numbers with unit multiplier (e.g. '50k records', '2 million rows', '2.5m accounts')
_PATTERN_WITH_MULT = re.compile(
    r"\b(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>k|m|b|thousand|million|millions|mn|billion|billions|bn)\b"
    r"(?:\s*(?P<noun>records?|rows?|entries|accounts?|users?|lines?|credentials?|emails?|passwords?|dumps?|profiles?|victims?|items?|cards?|logs?|files?|hits?|combos?))?",
    re.IGNORECASE,
)

# Regex for plain numbers or comma-formatted numbers with explicit entity noun (e.g. '1500 entries', '1,500,000 records')
_PATTERN_WITH_NOUN = re.compile(
    r"\b(?P<num>\d{1,3}(?:,\d{3})+|\d+)\s+"
    r"(?:records?|rows?|entries|accounts?|users?|lines?|credentials?|emails?|passwords?|dumps?|profiles?|victims?|items?|cards?|logs?|files?|hits?|combos?)\b",
    re.IGNORECASE,
)


def estimate_record_count(text: str) -> int:
    """
    Extracts an estimated record count from message text using heuristic regex matching.

    Supported patterns:
        - '50k records' -> 50,000
        - '2 million rows' -> 2,000,000
        - '1500 entries' -> 1,500
        - '2.5m accounts' -> 2,500,000
        - '10,000 users' -> 10,000

    Args:
        text: Raw text content to parse.

    Returns:
        int: Estimated record count, or default 1 if unidentifiable.
    """
    if not text or not isinstance(text, str):
        return 1

    candidates = []

    # 1. Check for multiplier-based expressions (50k, 2.5m, 2 million rows, etc.)
    for match in _PATTERN_WITH_MULT.finditer(text):
        try:
            raw_num = match.group("num").replace(",", ".")
            unit = match.group("unit").lower()
            multiplier = _MULTIPLIERS.get(unit, 1)
            count = int(float(raw_num) * multiplier)
            if count > 0:
                candidates.append(count)
        except (ValueError, TypeError):
            continue

    # 2. Check for explicit count + entity noun expressions (1500 entries, 500,000 lines)
    for match in _PATTERN_WITH_NOUN.finditer(text):
        try:
            raw_num = match.group("num").replace(",", "")
            count = int(raw_num)
            if count > 0:
                candidates.append(count)
        except (ValueError, TypeError):
            continue

    if candidates:
        # Return the largest candidate detected (e.g., 2.5m breach vs 100 sample lines)
        return max(candidates)

    return 1


def parse_scraped_message(
    message_text: str,
    message_date: Optional[str],
    message_id: str,
    channel_username: str,
    channel_title: Optional[str],
    breach_source_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Builds a normalized payload dictionary for an ingested Telegram message.

    Title format: '[Telegram] {channel_title}: {first_line_truncated_to_120_chars}'
    original_url format: 'https://t.me/{channel_username}/{message_id}'
    source_reference format: 'telegram_scrape:{channel_username}:{message_id}'

    Args:
        message_text: The scraped body text of the message.
        message_date: ISO datetime string from the message or None.
        message_id: Numerical or string message ID within the channel.
        channel_username: Public username of the channel without '@'.
        channel_title: Human-readable title of the channel.
        breach_source_id: Optional UUID/ID of the corresponding BreachSource.

    Returns:
        Dict[str, Any]: Structured payload ready for event bus publication.
    """
    clean_username = (channel_username or "").strip().lstrip("@")
    clean_msg_id = str(message_id).strip()

    # Determine first non-empty line for title
    first_line = ""
    for line in (message_text or "").splitlines():
        stripped = line.strip()
        if stripped:
            first_line = stripped
            break

    if not first_line:
        first_line = "Data Leak Alert"

    # Truncate first line to 120 characters
    first_line_truncated = first_line[:120].strip()
    display_title = (channel_title or clean_username or "Telegram Channel").strip()
    title = f"[Telegram] {display_title}: {first_line_truncated}"

    original_url = f"https://t.me/{clean_username}/{clean_msg_id}"
    source_reference = f"telegram_scrape:{clean_username}:{clean_msg_id}"

    # Fallback to current UTC datetime if message_date is missing or empty
    if message_date and str(message_date).strip():
        breach_date = str(message_date).strip()
    else:
        breach_date = datetime.utcnow().isoformat()

    description = (message_text or "").strip() or f"Scraped from {original_url}"
    record_count = estimate_record_count(message_text or "")

    return {
        "source_id": breach_source_id,
        "title": title,
        "description": description,
        "raw_content": message_text or "",
        "original_url": original_url,
        "source_reference": source_reference,
        "breach_date": breach_date,
        "record_count": record_count,
    }
