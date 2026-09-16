"""
LeakHunter V3 — Forum Scraper Integration Test

Tests the Playwright browser automation engine against a clearweb target
to verify that the headless browser launches, navigates, and extracts content.
This test does NOT require any login credentials.
"""

import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("forum_test")


async def test_playwright_browser():
    """Test 1: Verify Playwright can launch headless Chromium and load a page."""
    logger.info("TEST 1: Launching headless Chromium...")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0"
        )
        page = await context.new_page()

        await page.goto("https://example.com", wait_until="domcontentloaded", timeout=15000)
        title = await page.title()
        logger.info(f"  Page title: '{title}'")
        assert "Example Domain" in title, f"Unexpected title: {title}"
        logger.info("  ✅ TEST 1 PASSED: Browser launched and loaded page successfully.\n")

        await browser.close()


async def test_playwright_tor_proxy():
    """Test 2: Verify Playwright can route through Tor SOCKS5 proxy."""
    logger.info("TEST 2: Launching Chromium with Tor proxy...")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
            proxy={"server": "socks5://tor:9050"},
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0"
        )
        page = await context.new_page()

        try:
            await page.goto("https://check.torproject.org", wait_until="domcontentloaded", timeout=30000)
            body_text = await page.inner_text("body")
            is_tor = "Congratulations" in body_text or "using Tor" in body_text.lower()
            logger.info(f"  Tor check result: {'Using Tor ✅' if is_tor else 'NOT using Tor ❌'}")
            if is_tor:
                logger.info("  ✅ TEST 2 PASSED: Browser traffic is routed through Tor.\n")
            else:
                logger.warning("  ⚠️ TEST 2 WARNING: Could not confirm Tor routing. May be a Tor bootstrap delay.\n")
        except Exception as e:
            logger.warning(f"  ⚠️ TEST 2 WARNING: Tor proxy test failed (expected if Tor is still bootstrapping): {e}\n")

        await browser.close()


async def test_form_filling():
    """Test 3: Verify Playwright can locate and fill form fields (login simulation)."""
    logger.info("TEST 3: Testing form field detection and filling...")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context()
        page = await context.new_page()

        # Use httpbin.org form page as a test target
        await page.goto("https://httpbin.org/forms/post", wait_until="domcontentloaded", timeout=15000)

        # Find and fill form fields
        inputs = await page.query_selector_all("input")
        logger.info(f"  Found {len(inputs)} input fields on test form page.")
        assert len(inputs) > 0, "No input fields found"

        # Fill the customer name field
        await page.fill("input[name='custname']", "leakhunter_test")
        value = await page.input_value("input[name='custname']")
        assert value == "leakhunter_test", f"Fill failed, got: {value}"

        logger.info("  ✅ TEST 3 PASSED: Form detection and filling works correctly.\n")
        await browser.close()


async def test_content_extraction():
    """Test 4: Verify the scraper can extract structured text content from a page."""
    logger.info("TEST 4: Testing content extraction from a real page...")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context()
        page = await context.new_page()

        # Use Hacker News as a real-world content extraction test
        await page.goto("https://news.ycombinator.com", wait_until="domcontentloaded", timeout=15000)

        # Extract thread titles (similar to what we do on forums)
        titles = await page.query_selector_all("span.titleline > a")
        logger.info(f"  Found {len(titles)} thread titles on Hacker News.")
        assert len(titles) > 0, "No thread titles found"

        # Print first 5 titles
        for i, title_el in enumerate(titles[:5]):
            text = await title_el.inner_text()
            href = await title_el.get_attribute("href")
            logger.info(f"    [{i+1}] {text}")

        logger.info(f"\n  ✅ TEST 4 PASSED: Extracted {len(titles)} titles successfully.\n")
        await browser.close()


async def run_all_tests():
    logger.info("=" * 60)
    logger.info("LeakHunter V3 — Forum Scraper Integration Test Suite")
    logger.info("=" * 60 + "\n")

    await test_playwright_browser()
    await test_playwright_tor_proxy()
    await test_form_filling()
    await test_content_extraction()

    logger.info("=" * 60)
    logger.info("ALL TESTS COMPLETED")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
