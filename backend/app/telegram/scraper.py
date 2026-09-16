"""
LeakHunter V3 - Telegram Public Channel Scraper
Gathers threat intelligence by scraping public Telegram channel previews at
https://t.me/s/<channel_username> without requiring API keys or account credentials.
"""

import aiohttp
import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from bs4 import BeautifulSoup

from app.event_bus import event_bus
from app.telegram.keyword_filter import is_threat_relevant
from app.telegram.message_parser import parse_scraped_message

logger = logging.getLogger(__name__)


class TelegramScraper:
    """
    Scrapes public Telegram channel previews via web interface (https://t.me/s/<channel>)
    without requiring API keys, phone numbers, or Telegram credentials.
    """

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.scraped_message_ids: Set[str] = set()
        self.logger = logging.getLogger("TelegramScraper")
        self._user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        """Returns or initializes the active aiohttp ClientSession."""
        import socket
        if self.session is None or self.session.closed:
            headers = {"User-Agent": self._user_agent}
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(family=socket.AF_INET)
            self.session = aiohttp.ClientSession(headers=headers, timeout=timeout, connector=connector)
        return self.session

    async def close(self):
        """Closes the underlying aiohttp client session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def scrape_channel(
        self,
        channel_username: str,
        channel_title: Optional[str] = None,
        breach_source_id: Optional[str] = None,
        keyword_mode: str = "high_signal",
    ) -> Dict[str, Any]:
        """
        Scrapes the latest messages from a public Telegram channel preview.

        Args:
            channel_username: Channel handle (with or without '@').
            channel_title: Optional human-readable name for the channel.
            breach_source_id: Optional UUID/ID of the corresponding breach source.
            keyword_mode: Filter mode ('high_signal', 'low_signal', 'all').

        Returns:
            Dict[str, Any]: Summary dictionary with keys:
                - channel: str
                - messages_found: int
                - messages_ingested: int
                - errors: List[str]
        """
        clean_username = (channel_username or "").strip().lstrip("@")
        result: Dict[str, Any] = {
            "channel": clean_username,
            "messages_found": 0,
            "messages_ingested": 0,
            "errors": [],
        }

        if not clean_username:
            msg = "Channel username cannot be empty."
            self.logger.warning(msg)
            result["errors"].append(msg)
            return result

        url = f"https://t.me/s/{clean_username}"

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status != 200:
                    err_msg = f"HTTP {response.status} returned for {url}"
                    self.logger.warning(err_msg)
                    result["errors"].append(err_msg)
                    return result

                html = await response.text()
        except aiohttp.ClientError as exc:
            err_msg = f"Network connection error scraping {url}: {exc}"
            self.logger.warning(err_msg)
            result["errors"].append(err_msg)
            return result
        except asyncio.TimeoutError:
            err_msg = f"Request timed out while scraping {url}"
            self.logger.warning(err_msg)
            result["errors"].append(err_msg)
            return result
        except Exception as exc:
            err_msg = f"Unexpected error requesting {url}: {exc}"
            self.logger.error(err_msg, exc_info=True)
            result["errors"].append(err_msg)
            return result

        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as exc:
            err_msg = f"Failed to parse HTML for {url}: {exc}"
            self.logger.warning(err_msg)
            result["errors"].append(err_msg)
            return result

        # Auto-detect channel title from header if not provided
        if not channel_title:
            title_tag = soup.find("div", class_="tgme_channel_info_header_title")
            if title_tag:
                channel_title = title_tag.get_text().strip()
            elif soup.title:
                channel_title = soup.title.get_text().replace("Telegram: Contact @", "").strip()

        # Find all message widgets
        widgets = soup.find_all("div", class_="tgme_widget_message_wrap")
        if not widgets:
            widgets = soup.find_all("div", class_="tgme_widget_message")

        result["messages_found"] = len(widgets)
        self.logger.info("Channel @%s: Found %d message widgets.", clean_username, len(widgets))

        for widget in widgets:
            try:
                # 1. Extract message ID from data-post attribute
                data_post = widget.get("data-post")
                if not data_post:
                    inner_msg = widget.find("div", class_="tgme_widget_message")
                    if inner_msg:
                        data_post = inner_msg.get("data-post")

                if not data_post:
                    # Fallback to date link href if data-post is not present on div
                    date_link = widget.find("a", class_="tgme_widget_message_date")
                    if date_link and date_link.get("href"):
                        data_post = date_link.get("href").rstrip("/").split("t.me/")[-1]

                if not data_post:
                    self.logger.debug("Could not extract message ID (data-post) from widget in @%s, skipping.", clean_username)
                    continue

                # Format is typically 'channelname/12345' — extract the numeric/ID part
                msg_id = data_post.split("/")[-1] if "/" in data_post else data_post

                # 2. Extract message text
                text_elem = widget.find("div", class_="tgme_widget_message_text")
                if not text_elem:
                    # Skip media-only messages or messages without text body
                    continue

                message_text = text_elem.get_text(separator="\n").strip()
                if not message_text:
                    continue

                # 3. Extract datetime from time tag
                time_elem = widget.find("time")
                if time_elem and time_elem.has_attr("datetime"):
                    message_date = time_elem["datetime"]
                else:
                    message_date = datetime.utcnow().isoformat()

                # 4. Dedup key check
                dedup_key = f"{clean_username}:{msg_id}"
                if dedup_key in self.scraped_message_ids:
                    self.logger.debug("Message %s already scraped, skipping.", dedup_key)
                    continue

                # 5. Run keyword filter
                if not is_threat_relevant(message_text, keyword_mode):
                    self.logger.debug("Message %s did not match threat criteria (mode: %s).", dedup_key, keyword_mode)
                    continue

                # 6. Parse scraped message into event payload
                payload = parse_scraped_message(
                    message_text=message_text,
                    message_date=message_date,
                    message_id=msg_id,
                    channel_username=clean_username,
                    channel_title=channel_title or clean_username,
                    breach_source_id=breach_source_id,
                )

                # 7. Publish to event bus
                published = event_bus.publish("raw-leaks", payload)
                if not published:
                    self.logger.warning("Event bus failed to publish message %s", dedup_key)

                # 8. Record in deduplication set & increment counter
                self.scraped_message_ids.add(dedup_key)
                result["messages_ingested"] += 1
                self.logger.info("Ingested leak message %s from @%s: '%s'", msg_id, clean_username, payload["title"])

            except Exception as item_err:
                self.logger.warning("Unexpected structure or error in message widget: %s", item_err)
                continue

        return result

    async def run_polling_loop(self, channels: List[Dict[str, Any]], interval_seconds: int = 300):
        """
        Continuously polls public Telegram channels at the specified interval.

        Args:
            channels: List of channel configurations, e.g.:
                      [{'username': 'databreaches', 'title': 'Data Breaches', 'breach_source_id': '...', 'keyword_mode': 'high_signal'}]
            interval_seconds: Polling interval in seconds between scraping cycles.
        """
        self.logger.info(
            "Starting Telegram scraper polling loop for %d channels (interval: %ds).",
            len(channels),
            interval_seconds,
        )

        while True:
            cycle_found = 0
            cycle_ingested = 0

            for ch in channels:
                try:
                    username = ch.get("username") or ch.get("channel_username")
                    if not username:
                        self.logger.warning("Skipping channel entry missing 'username': %s", ch)
                        continue

                    title = ch.get("title") or ch.get("channel_title")
                    breach_source_id = ch.get("breach_source_id")
                    keyword_mode = ch.get("keyword_mode", "high_signal")

                    res = await self.scrape_channel(
                        channel_username=username,
                        channel_title=title,
                        breach_source_id=breach_source_id,
                        keyword_mode=keyword_mode,
                    )
                    cycle_found += res.get("messages_found", 0)
                    cycle_ingested += res.get("messages_ingested", 0)
                except Exception as exc:
                    self.logger.error("Error scraping channel %s: %s", ch, exc, exc_info=True)

            self.logger.info(
                "Telegram scraper cycle completed. Found: %d, Ingested: %d. Sleeping for %ds.",
                cycle_found,
                cycle_ingested,
                interval_seconds,
            )

            try:
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                self.logger.info("Telegram scraper polling loop cancelled, shutting down.")
                break
