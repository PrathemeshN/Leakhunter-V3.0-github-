import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.models import Base
from app.config import settings
async def init():
    engine = create_async_engine(settings.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://'))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Sync complete')
asyncio.run(init())