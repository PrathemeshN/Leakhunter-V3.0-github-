import aiohttp
import socket
import logging

logger = logging.getLogger(__name__)


async def resolve_domain_ip(domain: str) -> str:
    """
    DNS lookup to trace domain hosting.
    """
    try:
        # Run blocking socket resolver inside executor or simple async wrapper
        # For simplicity, direct socket gethostbyname is fine
        ip = socket.gethostbyname(domain)
        return ip
    except Exception:
        return "Unknown IP"


async def simulate_whois_lookup(domain: str) -> dict:
    """
    Simulates WHOIS lookup to extract registrar and owner details for tracing.
    """
    ip = await resolve_domain_ip(domain)
    
    # Pre-coded mock registry details for target domains
    if "apex-aerospace" in domain:
        return {
            "registrar": "GoDaddy.com, LLC",
            "owner": "Apex Aerospace Inc. Corp",
            "ip_address": ip,
            "country": "US",
            "hosting_provider": "Amazon Web Services (AWS)"
        }
    elif "medicare-plus" in domain:
        return {
            "registrar": "NameCheap, Inc.",
            "owner": "Medicare Plus Organization",
            "ip_address": ip,
            "country": "US",
            "hosting_provider": "DigitalOcean, LLC"
        }
        
    return {
        "registrar": "IANA Generic Registrar",
        "owner": "Redacted for Privacy",
        "ip_address": ip,
        "country": "Unknown",
        "hosting_provider": "Unknown Cloud Operator"
    }


async def traceback_threat_actor(usernames: list) -> list:
    """
    Simulates a Sherlock/OSINT username cross-reference search to check 
    if actor usernames are active on hacker forums or social platforms.
    """
    actor_matches = []
    
    # Common threat actor aliases from forum indicators
    target_actors = ["lockbit_official", "cyber_demon", "leak_lord", "breach_wizard", "kuro_hacker"]
    
    for username in usernames:
        username_clean = username.lower().strip()
        if username_clean in target_actors:
            # Found correlation
            actor_matches.append({
                "username": username,
                "correlated_platforms": ["Telegram Channels", "BreachForums", "X (Twitter)", "Exploit.in"],
                "threat_group_affinity": "Ransomware Affiliate / Intel Broker"
            })
            
    return actor_matches


async def run_traceback_analysis(domains: list, text: str) -> dict:
    """
    Executes domain traceback and username searches.
    """
    results = {
        "resolved_domains": [],
        "actor_correlations": []
    }
    
    # Tracing domains
    for d in domains[:3]:  # Limit to top 3 domains to prevent blocking
        whois_data = await simulate_whois_lookup(d)
        results["resolved_domains"].append({
            "domain": d,
            **whois_data
        })
        
    # Extract potential actor handles (e.g. from credit/signature lines in dump)
    # Simple regex search for handles
    signatures = re.findall(r'(?:by|hacked by|leaked by|author)\s*:\s*([\w_-]+)', text, re.IGNORECASE)
    if signatures:
        results["actor_correlations"] = await traceback_threat_actor(signatures)
        
    return results

import re # Ensure re is imported for signature search
