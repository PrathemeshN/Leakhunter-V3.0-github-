"""
LeakHunter V3 — Forum Scraper Background Worker

Loops every 15 minutes. For each active ForumIdentity that has a ForumAccount
and at least one online ForumMirror, launches the Playwright scraper to extract
new posts and publishes them to the raw-leaks event bus.
"""

import asyncio
import logging
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import ForumIdentity, ForumMirror, ForumAccount
from app.forum.scraper import ForumScraper
from app.forum.session_manager import load_session_cookies
from app.event_bus import event_bus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("forum_worker")


async def main():
    logger.info("Initializing LeakHunter V3 Forum Scraper Worker...")

    interval_seconds = 900  # 15 minutes
    scraper = ForumScraper(tor_proxy="socks5://tor:9050")

    while True:
        try:
            logger.info("Starting forum scrape cycle...")

            async with AsyncSessionLocal() as session:
                # Get all active forum identities
                stmt = select(ForumIdentity).where(ForumIdentity.is_active == True)
                result = await session.execute(stmt)
                forums = result.scalars().all()

                for forum in forums:
                    # Find an active account for this forum
                    acct_stmt = select(ForumAccount).where(
                        ForumAccount.forum_id == forum.id,
                        ForumAccount.is_active == True,
                    )
                    acct_result = await session.execute(acct_stmt)
                    account = acct_result.scalar_one_or_none()

                    if not account:
                        logger.debug(f"No active account for forum '{forum.name}'. Skipping.")
                        continue

                    # Find the best online mirror
                    mirror_stmt = select(ForumMirror).where(
                        ForumMirror.forum_id == forum.id,
                        ForumMirror.is_online == True,
                    ).order_by(ForumMirror.consecutive_failures.asc())
                    mirror_result = await session.execute(mirror_stmt)
                    mirror = mirror_result.scalar_one_or_none()

                    if not mirror:
                        logger.warning(f"No online mirrors for forum '{forum.name}'. Skipping.")
                        continue

                    logger.info(f"Scraping forum '{forum.name}' via {mirror.onion_url} as '{account.username}'")

                    # Load saved cookies
                    saved_cookies = await load_session_cookies(str(account.id))

                    # Determine forum config name from the forum identity name
                    config_name = forum.name.lower().replace(" ", "_").replace("-", "_")

                    # Run the scraper
                    posts = await scraper.scrape_forum(
                        forum_config_name=config_name,
                        base_url=mirror.onion_url,
                        account_id=str(account.id),
                        username=account.username,
                        password=account.password,
                        saved_cookies=saved_cookies,
                    )

                    # Publish to event bus
                    for payload in posts:
                        try:
                            event_bus.publish("raw-leaks", payload)
                            logger.info(f"Published forum post {payload['message_id']} to event bus.")
                        except Exception as e:
                            logger.error(f"Failed to publish post: {e}")

                    logger.info(f"Forum '{forum.name}' scrape completed. Found {len(posts)} threat posts.")

            logger.info(f"Forum scrape cycle completed. Sleeping for {interval_seconds}s.")

        except Exception as e:
            logger.error(f"Unexpected error in forum worker loop: {e}")

        await asyncio.sleep(interval_seconds)


if __name__ == '__main__':
    asyncio.run(main())
