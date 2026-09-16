"""
LeakHunter V3 - Telegram Threat Keyword Filter
Categorizes and filters incoming Telegram messages using high-signal and low-signal
threat intelligence keyword sets, spam rejection patterns, and length requirements.
"""

import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# High-signal threat keywords: automatic ingestion trigger
HIGH_SIGNAL_KEYWORDS: List[str] = [
    "database dump",
    "data breach",
    "leaked database",
    "combolist",
    "combo list",
    "fullz",
    "credit card dump",
    "ssn leak",
    "aadhaar leak",
    "credentials leak",
    "sql dump",
    "data leak",
    "ransomware",
    "exfiltrated",
    "millions of records",
    "user data",
    "leaked credentials",
    "password dump",
    "email:pass",
    "email:password",
    "bank leak",
    "medical records",
    "patient data",
    "corporate leak",
    "source code leak",
    "api keys leaked",
    "private keys",
    ".sql",
    ".csv dump",
    ".xlsx leak",
    "database exposed",
    "records leaked",
    "accounts compromised",
    "data for sale",
    "selling database",
    "free database",
    "fresh dump",
    "new leak",
]

# Low-signal threat keywords: ingested only when channel is trusted
LOW_SIGNAL_KEYWORDS: List[str] = [
    "hack",
    "hacked",
    "exploit",
    "vulnerability",
    "0day",
    "zero-day",
    "payload",
    "malware",
    "phishing",
    "carding",
    "stealer log",
    "botnet",
    "ddos",
    "rat",
    "backdoor",
    "shell access",
]

# Noise patterns: always reject messages matching these phrases
IGNORE_PATTERNS: List[str] = [
    "join our channel",
    "subscribe",
    "advertisement",
    "promo",
    "giveaway",
    "airdrop",
    "crypto signal",
    "forex signal",
]


def _matches_keyword(keyword: str, text_lower: str) -> bool:
    """
    Checks if a keyword exists in lowercase text.
    Uses regex word boundaries for short alphanumeric keywords (e.g. 'rat', 'ddos')
    to prevent false positives from substring collisions within normal vocabulary
    (e.g., matching 'rat' inside 'corporate' or 'separate').
    """
    if keyword.isalnum() and len(keyword) <= 4:
        return bool(re.search(rf"\b{re.escape(keyword)}\b", text_lower))
    return keyword in text_lower


def is_threat_relevant(text: str, keyword_mode: str = "high_signal") -> bool:
    """
    Evaluates whether a message is relevant for threat intelligence ingestion.

    Args:
        text: Raw text content of the Telegram message.
        keyword_mode: Matching mode:
            - 'all': Accepts any message that passes length and ignore checks.
            - 'high_signal': Requires at least one high-signal keyword (default).
            - 'low_signal': Accepts messages matching high- or low-signal keywords.

    Returns:
        bool: True if the message passes negative pattern checks, length >= 50,
              and satisfies the keyword requirement for the given mode.
    """
    if not text or len(text.strip()) < 50:
        return False

    text_lower = text.lower()

    # Reject spam, promotions, giveaways, and channel subscription prompts
    if any(pattern in text_lower for pattern in IGNORE_PATTERNS):
        return False

    mode = (keyword_mode or "high_signal").lower()

    if mode == "all":
        return True

    has_high = any(_matches_keyword(kw, text_lower) for kw in HIGH_SIGNAL_KEYWORDS)

    if mode == "high_signal":
        return has_high

    if mode == "low_signal":
        if has_high:
            return True
        return any(_matches_keyword(kw, text_lower) for kw in LOW_SIGNAL_KEYWORDS)

    # Fallback to high_signal if unknown mode provided
    return has_high


def get_signal_level(text: str) -> str:
    """
    Determines the threat signal level of a Telegram message.

    Args:
        text: Raw text content of the Telegram message.

    Returns:
        str: 'high' if matching high-signal keywords,
             'low' if matching low-signal keywords,
             'none' if matching ignore patterns, too short (<50 chars), or no keywords found.
    """
    if not text or len(text.strip()) < 50:
        return "none"

    text_lower = text.lower()

    if any(pattern in text_lower for pattern in IGNORE_PATTERNS):
        return "none"

    if any(_matches_keyword(kw, text_lower) for kw in HIGH_SIGNAL_KEYWORDS):
        return "high"

    if any(_matches_keyword(kw, text_lower) for kw in LOW_SIGNAL_KEYWORDS):
        return "low"

    return "none"
