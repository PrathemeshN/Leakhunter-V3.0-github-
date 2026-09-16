import asyncio
import logging
from sqlalchemy import select, update
from datetime import datetime

from app.database import AsyncSessionLocal
from app.models import ForumIdentity, ForumMirror
from app.resolver.health_prober import TorHealthProber

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mirror_worker")

async def main():
    logger.info("Initializing LeakHunter V3 Dark Web Mirror Registry Worker...")
    
    interval_seconds = 600  # Run every 10 minutes
    prober = TorHealthProber(tor_proxy="tor:9050")
    
    while True:
        try:
            logger.info("Starting health check cycle for all registered forum mirrors...")
            
            async with AsyncSessionLocal() as session:
                # Fetch all mirrors
                stmt = select(ForumMirror)
                result = await session.execute(stmt)
                mirrors = result.scalars().all()
                
                if not mirrors:
                    logger.info("No forum mirrors found in the registry. Sleeping...")
                
                for mirror in mirrors:
                    is_alive = await prober.ping_onion(mirror.onion_url)
                    
                    if is_alive:
                        logger.info(f"[*] ONLINE: {mirror.onion_url}")
                        mirror.is_online = True
                        mirror.consecutive_failures = 0
                    else:
                        logger.warning(f"[!] OFFLINE: {mirror.onion_url}")
                        mirror.consecutive_failures += 1
                        if mirror.consecutive_failures >= 3:
                            mirror.is_online = False
                            
                    mirror.last_tested_at = datetime.utcnow()
                    
                    # Save changes
                    session.add(mirror)
                    await session.commit()
                    
            logger.info(f"Mirror health check cycle completed. Sleeping for {interval_seconds}s.")
            
        except Exception as e:
            logger.error(f"Unexpected error in mirror worker loop: {e}")
            
        await asyncio.sleep(interval_seconds)

if __name__ == '__main__':
    asyncio.run(main())
