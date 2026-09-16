"""
LeakHunter V3 — Forum Session Manager

Handles saving/loading browser cookies to the database so the scraper
doesn't need to re-login every cycle. Detects expired sessions.
"""

import logging
from datetime import datetime
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import ForumAccount

logger = logging.getLogger(__name__)


async def load_session_cookies(forum_account_id: str) -> list | None:
    """
    Loads saved browser cookies for a forum account from the database.
    Returns a list of cookie dicts, or None if no session exists.
    """
    async with AsyncSessionLocal() as session:
        stmt = select(ForumAccount).where(ForumAccount.id == forum_account_id)
        result = await session.execute(stmt)
        account = result.scalar_one_or_none()

        if account and account.session_cookies:
            logger.info(f"Loaded saved session cookies for account {account.username}")
            return account.session_cookies

    return None


async def save_session_cookies(forum_account_id: str, cookies: list):
    """
    Persists browser cookies to the database after a successful login or scrape.
    """
    async with AsyncSessionLocal() as session:
        stmt = select(ForumAccount).where(ForumAccount.id == forum_account_id)
        result = await session.execute(stmt)
        account = result.scalar_one_or_none()

        if account:
            account.session_cookies = cookies
            account.last_login_at = datetime.utcnow()
            session.add(account)
            await session.commit()
            logger.info(f"Saved session cookies for account {account.username}")


async def update_scrape_stats(forum_account_id: str, posts_found: int):
    """
    Updates the last_scrape_at timestamp and increments posts_scraped counter.
    """
    async with AsyncSessionLocal() as session:
        stmt = select(ForumAccount).where(ForumAccount.id == forum_account_id)
        result = await session.execute(stmt)
        account = result.scalar_one_or_none()

        if account:
            account.last_scrape_at = datetime.utcnow()
            account.posts_scraped = (account.posts_scraped or 0) + posts_found
            session.add(account)
            await session.commit()
