import hashlib
import re


def normalize_text(text: str) -> str:
    """
    Standardizes whitespace, strips characters, and lowercases text.
    """
    if not text:
        return ""
    # Remove HTML tags if present
    text = re.sub(r'<[^>]*>', ' ', text)
    # Replace multiple whitespaces/newlines with a single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def compute_content_hash(text: str) -> str:
    """
    Computes a SHA-256 hash of normalized text for deduplication.
    """
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def extract_domains_from_text(text: str) -> list:
    """
    Helper to parse potential company domains from text.
    """
    # Basic email/domain finder
    emails = re.findall(r'[\w\.-]+@([\w\.-]+\.\w+)', text)
    # Basic domain finder
    urls = re.findall(r'\b(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+)\b', text)
    
    domains = set()
    for d in emails + urls:
        d_lower = d.lower().strip()
        # Filter out common noise
        if d_lower not in ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com", "github.com"]:
            # Clean protocol/subdomains if captured in URL pattern
            parts = d_lower.split(".")
            if len(parts) >= 2:
                # keep domain.com or domain.co.uk
                domains.add(".".join(parts[-2:]))
    return list(domains)
