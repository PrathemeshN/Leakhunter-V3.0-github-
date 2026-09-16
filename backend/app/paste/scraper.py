import aiohttp
import asyncio
import logging
import re
from bs4 import BeautifulSoup
from datetime import datetime

# Reuse the Telegram keyword filter for threat matching
from app.telegram.keyword_filter import is_threat_relevant

logger = logging.getLogger(__name__)

class PastebinScraper:
    """
    Public web scraper for Pastebin.com archive.
    Periodically checks https://pastebin.com/archive for new text pastes,
    extracts the IDs, fetches the raw text, and filters out noise.
    """

    ARCHIVE_URL = "https://pastebin.com/archive"
    RAW_BASE_URL = "https://pastebin.com/raw"

    def __init__(self, request_delay: float = 1.0):
        """
        Args:
            request_delay: Wait time between scraping raw pastes to avoid IP bans.
        """
        self.request_delay = request_delay
        self.seen_ids = set()

    async def fetch_archive(self, session: aiohttp.ClientSession) -> list:
        """
        Fetches the archive page and extracts recent paste IDs.
        """
        try:
            async with session.get(self.ARCHIVE_URL, timeout=10) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    # Pastebin archive links look like <a href="/cRs1uEaY"> or <a href="/cRs1uEaY?source=archive">
                    # Using regex to find 8-char alphanumeric IDs
                    matches = set(re.findall(r'href="/([a-zA-Z0-9]{8})(?:\?source=archive)?"', html))
                    
                    # Remove anything that's clearly a route, not an ID
                    ignore_routes = {"doc_api", "pro_api", "contact", "privacy", "cookies", "sitemap", "archive"}
                    valid_ids = [m for m in matches if m.lower() not in ignore_routes]
                    
                    return valid_ids
                else:
                    logger.warning(f"Failed to fetch Pastebin archive. HTTP {resp.status}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching Pastebin archive: {e}")
            return []

    async def fetch_raw_paste(self, session: aiohttp.ClientSession, paste_id: str) -> str:
        """
        Fetches the raw text content for a specific paste ID.
        """
        url = f"{self.RAW_BASE_URL}/{paste_id}"
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.text()
        except Exception as e:
            logger.debug(f"Failed to fetch raw paste {paste_id}: {e}")
        return ""

    async def poll_recent_pastes(self) -> list:
        """
        Main method to poll the archive, fetch unseen pastes, and filter for threats.
        Returns a list of payloads ready for the event bus.
        """
        extracted_leaks = []
        
        async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}) as session:
            recent_ids = await self.fetch_archive(session)
            
            new_ids = [pid for pid in recent_ids if pid not in self.seen_ids]
            if not new_ids:
                return []
                
            logger.info(f"Found {len(new_ids)} new pastes to inspect.")
            
            for paste_id in new_ids:
                # Add to seen immediately so we don't double process if it crashes
                self.seen_ids.add(paste_id)
                # Cap the memory of seen_ids to 10000
                if len(self.seen_ids) > 10000:
                    self.seen_ids.clear()
                    
                raw_text = await self.fetch_raw_paste(session, paste_id)
                
                # Check for threats using our high_signal filter
                if raw_text and is_threat_relevant(raw_text, keyword_mode="high_signal"):
                    logger.info(f"Threat keyword match found in paste: {paste_id}")
                    
                    payload = {
                        "source": "pastebin",
                        "channel_id": "pastebin_archive",
                        "channel_title": "Pastebin Archive",
                        "message_id": paste_id,
                        "text": raw_text,
                        "date": datetime.utcnow().isoformat(),
                        "url": f"https://pastebin.com/{paste_id}",
                    }
                    extracted_leaks.append(payload)
                
                # Gentle scraping delay
                await asyncio.sleep(self.request_delay)
                
        return extracted_leaks
