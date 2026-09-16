from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
    pool_recycle=1800,  # Recycle connections after 30 mins to prevent stale connections
    pool_pre_ping=True, # Verify connection is alive before using it
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # Auto-seed default admin account
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        from app.models import User
        
        try:
            result = await session.execute(select(User))
            users = result.scalars().all()
            
            if not users:
                import bcrypt
                salt = bcrypt.gensalt()
                hashed = bcrypt.hashpw("Kuro@2005".encode('utf-8'), salt).decode('utf-8')
                
                admin_user = User(
                    email="admin@leakhunter.ai",
                    hashed_password=hashed,
                    role="admin",
                    is_active=True
                )
                session.add(admin_user)
                await session.commit()
                print("Default admin account seeded successfully: admin@leakhunter.ai / Kuro@2005")
        except Exception as e:
            print(f"Database seeding skipped/failed: {e}")
            await session.rollback()
