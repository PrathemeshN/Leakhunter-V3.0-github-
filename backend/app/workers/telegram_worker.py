import asyncio
import logging
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import TelegramChannel
from app.telegram.scraper import TelegramScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("telegram_worker")

DEFAULT_CHANNELS = [
    {'username': 'dabordstest', 'title': 'Test Channel', 'keyword_mode': 'all'},
]


async def main():
    logger.info("Initializing LeakHunter V3 Telegram Scraper Worker...")

    channels = []
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(TelegramChannel).where(TelegramChannel.is_active == True)
            result = await session.execute(stmt)
            db_channels = result.scalars().all()

            if db_channels:
                channels = [
                    {
                        'username': ch.channel_username,
                        'title': ch.channel_title,
                        'breach_source_id': ch.breach_source_id,
                        'keyword_mode': ch.keyword_mode or 'all',
                    }
                    for ch in db_channels
                ]
                logger.info(f"Loaded {len(channels)} active channel(s) from database.")
    except Exception as e:
        logger.error(f"Error querying active Telegram channels from database: {e}")

    if not channels:
        logger.info("Database query returned empty or failed. Falling back to default channels.")
        channels = DEFAULT_CHANNELS

    scraper = TelegramScraper()
    await scraper.run_polling_loop(channels, interval_seconds=300)


if __name__ == '__main__':
    asyncio.run(main())
