import asyncio
import logging
from app.paste.scraper import PastebinScraper
from app.event_bus import event_bus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("paste_worker")

async def main():
    logger.info("Initializing LeakHunter V3 Paste Site Scraper Worker...")
    
    # 60 seconds interval for polling recent pastes
    interval_seconds = 60
    scraper = PastebinScraper(request_delay=1.0)
    
    logger.info(f"Starting Pastebin archive polling loop (interval: {interval_seconds}s).")
    
    while True:
        try:
            extracted_leaks = await scraper.poll_recent_pastes()
            
            # Push found leaks to the event bus
            if extracted_leaks:
                for payload in extracted_leaks:
                    try:
                        event_bus.publish("raw-leaks", payload)
                        logger.info(f"Published paste {payload['message_id']} to event bus.")
                    except Exception as e:
                        logger.error(f"Failed to publish paste {payload['message_id']}: {e}")
            
            logger.info(f"Paste scraper cycle completed. Found: {len(extracted_leaks)}. Sleeping for {interval_seconds}s.")
        except Exception as e:
            logger.error(f"Unexpected error in paste polling loop: {e}")
            
        await asyncio.sleep(interval_seconds)

if __name__ == '__main__':
    asyncio.run(main())
