import aiohttp
from app.config import settings
import logging

logger = logging.getLogger(__name__)


async def verify_leak_authenticity(emails: list, domains: list, category: str) -> int:
    """
    Cross-checks extracted identifiers with breach intelligence databases (HIBP simulator).
    Returns confirmation code:
      0 = Unverified (default)
      1 = Verified Authentic
      2 = Disputed / False Positive
    """
    if not emails and not domains:
        return 0
        
    # Real HaveIBeenPwned lookup if API key is provided
    if settings.HIBP_API_KEY and emails:
        target_email = emails[0]
        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{target_email}"
        headers = {
            "hibp-api-key": settings.HIBP_API_KEY,
            "user-agent": "LeakHunterV2-Intel-Client"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=5) as resp:
                    if resp.status == 200:
                        # Found active pwned account, corroborating authenticity
                        return 1
                    elif resp.status == 404:
                        # Not in current public list, but could be a new zero-day leak
                        pass
        except Exception as e:
            logger.warning(f"HIBP API check failed/timed out: {e}")
            
    # Mock / Sandbox heuristic verification for local development
    # Verifies the leak if it contains known corporate domains or common breach signatures
    high_value_domains = ["apex-aerospace.com", "medicare-plus.org", "nexon-financial.net", "corporate.net"]
    
    # Heuristics:
    # 1. Any leak containing high-value target domains is verified as authentic threat intel
    for domain in domains:
        if domain.lower() in high_value_domains:
            return 1
            
    # 2. If it's credential type and we extracted multiple credentials, verify it
    if category == "credentials" and len(emails) >= 2:
        return 1
        
    # 3. Default to unverified status requiring analyst review
    return 0


def calculate_confidence_score(source_reference: str, raw_content: str, confirmed_authentic: int, data_types: list) -> float:
    '''
    Calculates a 0-100 confidence score based on:
    1. Source Credibility (e.g., highly credible forums vs anonymous pastebin)
    2. Proof / Artifact Presence (sample data, screenshots, db structures in raw_content)
    3. Vendor Authenticity (HIBP or direct validation)
    '''
    score = 0.0

    # 1. Source Credibility
    if 'breachforums' in source_reference.lower() or 'xss.is' in source_reference.lower() or 'vxunderground' in source_reference.lower():
        score += 35.0  # High credibility tier 1 sources
    elif 'telegram' in source_reference.lower():
        score += 20.0  # Medium credibility
    elif 'pastebin' in source_reference.lower():
        score += 10.0  # Low/anonymous credibility
    else:
        score += 15.0

    # 2. Proofs backing up claims
    content_lower = raw_content.lower()
    proof_keywords = ['sample', 'proof', 'screenshot', 'csv', 'sql', 'database snippet', 'row count', 'dump']
    proof_score = sum(5.0 for kw in proof_keywords if kw in content_lower)
    score += min(30.0, proof_score)  # Cap proof score at 30

    # Extra points for actual structured data parsing success
    if len(data_types) > 2:
        score += 10.0

    # 3. Authenticity Validation (HIBP, etc.)
    if confirmed_authentic == 1:
        score += 25.0

    return min(100.0, round(score, 1))
