"""
LeakHunter V3 — Playwright Forum Scraper

Uses headless Chromium to log into forums (clearweb or .onion via Tor),
navigate thread listings, and extract post content for the ML pipeline.
"""

import asyncio
import logging
from datetime import datetime
from playwright.async_api import async_playwright, Page, BrowserContext

from app.forum.forum_configs import get_forum_config
from app.forum.session_manager import load_session_cookies, save_session_cookies, update_scrape_stats
from app.telegram.keyword_filter import is_threat_relevant

logger = logging.getLogger(__name__)


class ForumScraper:
    """
    Browser-automation scraper that can authenticate with forums
    and extract thread/post content using Playwright.
    """

    def __init__(self, tor_proxy: str = "socks5://tor:9050"):
        self.tor_proxy = tor_proxy
        self.seen_thread_urls = set()

    async def scrape_forum(
        self,
        forum_config_name: str,
        base_url: str,
        account_id: str,
        username: str,
        password: str,
        saved_cookies: list | None = None,
    ) -> list:
        """
        Main entry point. Launches a browser, logs in, scrapes threads,
        and returns a list of extracted post payloads.
        """
        config = get_forum_config(forum_config_name)
        if not config:
            logger.error(f"No forum config found for '{forum_config_name}'")
            return []

        extracted_posts = []

        async with async_playwright() as pw:
            # Launch browser — route through Tor if needed
            launch_args = {
                "headless": True,
                "args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
            }
            if config.get("use_tor", False):
                launch_args["proxy"] = {"server": self.tor_proxy}

            browser = await pw.chromium.launch(**launch_args)

            try:
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0",
                    viewport={"width": 1280, "height": 800},
                )

                # Load saved cookies if available
                if saved_cookies:
                    await context.add_cookies(saved_cookies)
                    logger.info("Loaded saved session cookies into browser context.")

                page = await context.new_page()

                # Step 1: Check if session is still valid
                logged_in = await self._check_login_status(page, base_url, config)

                # Step 2: Login if needed
                if not logged_in:
                    logger.info(f"Session expired or no cookies. Logging in as '{username}'...")
                    logged_in = await self._perform_login(page, base_url, config, username, password)

                    if logged_in:
                        # Save fresh cookies
                        cookies = await context.cookies()
                        await save_session_cookies(account_id, cookies)
                    else:
                        logger.error(f"Login failed for '{username}' on {base_url}")
                        return []

                # Step 3: Scrape threads
                extracted_posts = await self._scrape_threads(page, base_url, config, forum_config_name)

                # Step 4: Update stats
                await update_scrape_stats(account_id, len(extracted_posts))

            except Exception as e:
                logger.error(f"Error during forum scrape: {e}")
            finally:
                await browser.close()

        return extracted_posts

    async def _check_login_status(self, page: Page, base_url: str, config: dict) -> bool:
        """Navigate to base URL and check if we're already logged in."""
        try:
            await page.goto(base_url, wait_until="domcontentloaded", timeout=30000)
            indicator = config.get("login_success_indicator")
            if indicator:
                element = await page.query_selector(indicator)
                if element:
                    logger.info("Session is still valid — already logged in.")
                    return True
        except Exception as e:
            logger.debug(f"Login status check failed: {e}")
        return False

    async def _perform_login(self, page: Page, base_url: str, config: dict, username: str, password: str) -> bool:
        """Fill in the login form and submit."""
        try:
            login_url = base_url.rstrip("/") + config["login_url_path"]
            await page.goto(login_url, wait_until="domcontentloaded", timeout=30000)

            # Fill credentials
            await page.fill(config["username_field"], username)
            await page.fill(config["password_field"], password)

            # Submit
            await page.click(config["submit_button"])
            await page.wait_for_load_state("domcontentloaded", timeout=15000)

            # Wait a bit for redirect
            await asyncio.sleep(2)

            # Check if login succeeded
            indicator = config.get("login_success_indicator")
            if indicator:
                element = await page.query_selector(indicator)
                if element:
                    logger.info("Login successful!")
                    return True

            logger.warning("Login may have failed — success indicator not found.")
            return False

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    async def _scrape_threads(self, page: Page, base_url: str, config: dict, forum_name: str) -> list:
        """Navigate to thread listing and extract posts."""
        extracted = []

        try:
            thread_list_url = base_url.rstrip("/") + config["thread_list_url_path"]
            await page.goto(thread_list_url, wait_until="domcontentloaded", timeout=30000)

            # Find thread links
            thread_links = await page.query_selector_all(config["thread_link_selector"])
            logger.info(f"Found {len(thread_links)} threads on listing page.")

            # Collect thread URLs (limit to first 20 to avoid overloading)
            thread_urls = []
            for link in thread_links[:20]:
                href = await link.get_attribute("href")
                title = (await link.inner_text()).strip()

                if href:
                    full_url = href if href.startswith("http") else base_url.rstrip("/") + "/" + href.lstrip("/")
                    if full_url not in self.seen_thread_urls:
                        thread_urls.append({"url": full_url, "title": title})
                        self.seen_thread_urls.add(full_url)

            # Cap seen URLs memory
            if len(self.seen_thread_urls) > 5000:
                self.seen_thread_urls.clear()

            logger.info(f"Found {len(thread_urls)} new threads to scrape.")

            # Scrape each thread
            for thread in thread_urls:
                try:
                    posts = await self._extract_thread_posts(page, thread["url"], thread["title"], config, forum_name, base_url)
                    extracted.extend(posts)
                    await asyncio.sleep(1)  # Be gentle
                except Exception as e:
                    logger.debug(f"Error scraping thread {thread['url']}: {e}")

        except Exception as e:
            logger.error(f"Error navigating thread listing: {e}")

        return extracted

    async def _extract_thread_posts(self, page: Page, thread_url: str, thread_title: str, config: dict, forum_name: str, base_url: str) -> list:
        """Navigate into a thread and extract individual post content."""
        posts = []

        try:
            await page.goto(thread_url, wait_until="domcontentloaded", timeout=30000)

            post_elements = await page.query_selector_all(config["post_content_selector"])
            author_elements = await page.query_selector_all(config["post_author_selector"])

            for i, post_el in enumerate(post_elements):
                text = (await post_el.inner_text()).strip()

                # Get author if available
                author = "unknown"
                if i < len(author_elements):
                    author = (await author_elements[i].inner_text()).strip()

                # Only ingest posts that pass threat keyword filter
                if text and is_threat_relevant(text, keyword_mode="high_signal"):
                    payload = {
                        "source": f"forum_{forum_name}",
                        "channel_id": forum_name,
                        "channel_title": f"Forum: {forum_name}",
                        "message_id": f"{forum_name}_{hash(thread_url + text) & 0xFFFFFFFF:08x}",
                        "text": f"[Thread: {thread_title}] [Author: {author}]\n\n{text}",
                        "date": datetime.utcnow().isoformat(),
                        "url": thread_url,
                    }
                    posts.append(payload)
                    logger.info(f"Threat match in thread '{thread_title}' by {author}")

        except Exception as e:
            logger.debug(f"Error extracting posts from {thread_url}: {e}")

        return posts
