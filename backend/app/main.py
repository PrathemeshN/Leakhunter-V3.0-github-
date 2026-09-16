from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict, Any
import json
import logging
import asyncio

# Security imports
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta

# Project imports
from app.config import settings
from app.database import init_db, get_db, AsyncSessionLocal
from app.models import User, DataBreach, BreachSource, ScraperLog, TelegramChannel
from app.elasticsearch_client import init_elasticsearch, search_breaches
from app.event_bus import event_bus
from app.pipeline.classifier import train_model
from app.schemas import UserCreate, UserResponse, Token, BreachSourceCreate, ScrapedLeakPayload, TrainPayload

# Redis for WebSocket subscription
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict, Any
import json
import logging
import asyncio

# Security imports
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta

# Project imports
from app.config import settings
from app.database import init_db, get_db, AsyncSessionLocal
from app.models import User, DataBreach, BreachSource, ScraperLog, TelegramChannel
from app.elasticsearch_client import init_elasticsearch, search_breaches
from app.event_bus import event_bus
from app.pipeline.classifier import train_model
from app.schemas import UserCreate, UserResponse, Token, BreachSourceCreate, ScrapedLeakPayload, TrainPayload

# Redis for WebSocket subscription
import redis
redis_client = redis.from_url(settings.REDIS_URL)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("leakhunter_api")

app = FastAPI(
    title="LeakHunter AI - Threat Intelligence API",
    version="2.0",
    description="Production-grade API for automated data leak detection, classification, and OSINT traceback"
)

from app.routers.auth import router as auth_router
app.include_router(auth_router)

# Production Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "https://leakhunter.ai"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Security setup
import bcrypt
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password, hashed_password):
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user


@app.on_event("startup")
async def startup_event():
    logger.info("Initializing LeakHunter V2 Services...")
    await init_db()
    await init_elasticsearch()


# --- Authentication Routes ---

@app.post("/api/v1/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    existing = await db.execute(select(User).where(User.email == user_data.email))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_pwd = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_pwd,
        role="admin",  # Default to admin for easier local configuration
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@app.post("/api/v1/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "email": user.email
    }


# --- Scrapers & Feed Admin ---

@app.post("/api/v1/scrapers")
async def create_scraper(source: BreachSourceCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing = await db.execute(select(BreachSource).where(BreachSource.name == source.name))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Scraper name already exists")
        
    new_source = BreachSource(
        name=source.name,
        url=source.url,
        source_type=source.source_type,
        reliability_score=source.reliability_score,
        scrape_frequency_minutes=source.scrape_frequency_minutes,
        config=source.config,
        is_active=1
    )
    db.add(new_source)
    await db.commit()
    await db.refresh(new_source)
    return new_source


@app.get("/api/v1/scrapers")
async def list_scrapers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BreachSource))
    return result.scalars().all()


# --- Simulate Raw Scrape Ingestion ---

@app.post("/api/v1/simulate-scrape")
async def simulate_scrape(payload: ScrapedLeakPayload):
    """
    Directly pushes a scraped leak record to the Event Queue to test 
    ingestion, NLP extraction, scikit-learn classification, and Elasticsearch indexing.
    """
    event = {
        "source_id": payload.source_id,
        "title": payload.title,
        "description": payload.description,
        "raw_content": payload.raw_content,
        "original_url": payload.original_url,
        "source_reference": payload.source_reference,
        "breach_date": payload.breach_date or datetime.utcnow().isoformat(),
        "record_count": payload.record_count
    }
    
    published = event_bus.publish("raw-leaks", event)
    if published:
        return {"status": "success", "message": "Scraped payload published to raw-leaks topic."}
    else:
        raise HTTPException(status_code=500, detail="Failed to publish to broker queue.")


# --- Search & Queries ---

@app.get("/api/v1/search")
async def search_index(q: str = "", min_sev: int = 0, current_user: User = Depends(get_current_user)):
    """
    Queries full-text index via Elasticsearch.
    """
    filters = {}
    if min_sev > 0:
        filters["min_severity"] = min_sev
    hits = await search_breaches(q, filters)
    return hits


@app.get("/api/v1/breaches")
async def get_breaches(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Fetches processed breaches from TimescaleDB database.
    """
    result = await db.execute(select(DataBreach).order_by(DataBreach.discovered_date.desc()).limit(100))
    return result.scalars().all()


# --- Analytics & Charts Dashboard ---

@app.get("/api/v1/stats")
async def get_analytics(db: AsyncSession = Depends(get_db)):
    """
    Compiles database statistics for the frontend dashboard widgets.
    """
    # Totals
    total_breaches = await db.execute(select(func.count(DataBreach.id)))
    total_records = await db.execute(select(func.sum(DataBreach.record_count)))
    avg_severity = await db.execute(select(func.avg(DataBreach.severity_score)))
    
    total_breaches_val = total_breaches.scalar() or 0
    total_records_val = total_records.scalar() or 0
    avg_severity_val = int(avg_severity.scalar() or 0)
    
    # Classification Distribution
    # Query SQL array categories
    classification_counts = {
        "credentials": 0,
        "pii": 0,
        "financial": 0,
        "health": 0,
        "corporate": 0,
        "other": 0
    }
    
    # Simple count approximations for local development dashboard charts
    for category in classification_counts.keys():
        cnt = await db.execute(select(func.count(DataBreach.id)).where(DataBreach.data_types.any(category)))
        classification_counts[category] = cnt.scalar() or 0
        
    # Timeline trend data (grouped by date)
    timeline_result = await db.execute(
        select(
            func.date_trunc('day', DataBreach.discovered_date).label('day'),
            func.count(DataBreach.id).label('count')
        )
        .group_by('day')
        .order_by('day')
        .limit(30)
    )
    
    timeline = []
    for row in timeline_result.all():
        timeline.append({
            "date": row.day.strftime("%Y-%m-%d"),
            "count": row.count
        })
        
    # Fallback default timeline data for empty state dashboards
    if not timeline:
        timeline = [{"date": datetime.utcnow().strftime("%Y-%m-%d"), "count": total_breaches_val}]

    return {
        "totalBreaches": total_breaches_val,
        "totalRecords": total_records_val,
        "avgSeverity": avg_severity_val,
        "classifications": classification_counts,
        "timeline": timeline
    }


# --- ML Custom Classifier Training ---

@app.post("/api/v1/train")
async def retrain_classifier(payload: TrainPayload, current_user: User = Depends(get_current_user)):
    """
    Retrains the scikit-learn TF-IDF + Random Forest model using user-submitted texts and labels.
    """
    if len(payload.texts) < 5:
        raise HTTPException(status_code=400, detail="At least 5 training samples are required.")
        
    success = train_model(payload.texts, payload.labels)
    if success:
        return {"status": "success", "message": "Model retrained and saved successfully."}
    else:
        raise HTTPException(status_code=500, detail="Model retraining failed.")


# --- Telegram Channel Management ---

@app.post("/api/v1/telegram/channels")
async def add_telegram_channel(
    channel_username: str,
    channel_title: str = "Unknown Channel",
    keyword_mode: str = "high_signal",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a new Telegram channel to the monitoring list.
    The telegram_scraper worker will automatically pick it up on its next polling cycle.
    """
    # Clean username
    channel_username = channel_username.strip().lstrip("@").lower()
    
    # Check for duplicates
    existing = await db.execute(
        select(TelegramChannel).where(TelegramChannel.channel_username == channel_username)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail=f"Channel @{channel_username} is already being monitored.")
    
    # Auto-create a linked BreachSource
    import uuid as uuid_mod
    source_id = uuid_mod.uuid4()
    new_source = BreachSource(
        id=source_id,
        name=f"Telegram: @{channel_username}",
        url=f"https://t.me/s/{channel_username}",
        source_type="telegram",
        reliability_score=50,
        is_active=1,
    )
    db.add(new_source)
    
    # Create TelegramChannel record
    new_channel = TelegramChannel(
        channel_username=channel_username,
        channel_title=channel_title,
        keyword_mode=keyword_mode,
        breach_source_id=source_id,
        is_active=True,
    )
    db.add(new_channel)
    await db.commit()
    await db.refresh(new_channel)
    
    return {
        "status": "success",
        "message": f"Channel @{channel_username} added to monitoring list.",
        "channel_id": str(new_channel.id),
        "breach_source_id": str(source_id),
        "scrape_url": f"https://t.me/s/{channel_username}",
    }


@app.get("/api/v1/telegram/channels")
async def list_telegram_channels(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all tracked Telegram channels with monitoring status."""
    result = await db.execute(select(TelegramChannel).order_by(TelegramChannel.created_at.desc()))
    channels = result.scalars().all()
    
    return [
        {
            "id": str(ch.id),
            "channel_username": ch.channel_username,
            "channel_title": ch.channel_title,
            "is_active": ch.is_active,
            "keyword_mode": ch.keyword_mode,
            "reliability_score": ch.reliability_score,
            "messages_captured": ch.messages_captured,
            "last_scraped_at": ch.last_scraped_at.isoformat() if ch.last_scraped_at else None,
        }
        for ch in channels
    ]


@app.delete("/api/v1/telegram/channels/{channel_id}")
async def remove_telegram_channel(
    channel_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Stop monitoring a Telegram channel."""
    import uuid as uuid_mod
    result = await db.execute(
        select(TelegramChannel).where(TelegramChannel.id == uuid_mod.UUID(channel_id))
    )
    channel = result.scalars().first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found.")
    
    channel.is_active = False
    await db.commit()
    return {"status": "success", "message": f"Stopped monitoring @{channel.channel_username}."}


@app.post("/api/v1/telegram/scrape-now/{channel_username}")
async def trigger_manual_scrape(
    channel_username: str,
    current_user: User = Depends(get_current_user)
):
    """
    Trigger an immediate one-off scrape of a Telegram channel.
    Useful for testing or manually capturing a known active leak channel.
    """
    from app.telegram.scraper import TelegramScraper
    
    channel_username = channel_username.strip().lstrip("@").lower()
    scraper = TelegramScraper()
    result = await scraper.scrape_channel(
        channel_username=channel_username,
        channel_title=channel_username,
        keyword_mode="all"  # Manual trigger = ingest everything
    )
    return result


@app.get("/api/v1/telegram/stats")
async def telegram_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Telegram monitoring statistics."""
    total_channels = await db.execute(select(func.count(TelegramChannel.id)))
    active_channels = await db.execute(
        select(func.count(TelegramChannel.id)).where(TelegramChannel.is_active == True)
    )
    total_captured = await db.execute(select(func.sum(TelegramChannel.messages_captured)))
    
    return {
        "total_channels": total_channels.scalar() or 0,
        "active_channels": active_channels.scalar() or 0,
        "total_messages_captured": total_captured.scalar() or 0,
    }


# --- Live WebSockets Alert Dispatcher ---

@app.websocket("/api/v1/alerts/ws")
async def websocket_alerts_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("New WebSocket client connected for live threat alerts.")
    
    # Create Redis pubsub client to subscribe to threat alert notifications
    pubsub = redis_client.pubsub()
    pubsub.subscribe("threat_alerts")
    
    try:
        # Loop listening for events published from consumer.py and streaming to React client
        while True:
            # Check for messages (non-blocking poll to prevent WebSocket locking)
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
            if message:
                payload = json.loads(message['data'].decode('utf-8'))
                await websocket.send_json(payload)
            # Yield control back to loop
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket execution error: {e}")
    finally:
        pubsub.unsubscribe("threat_alerts")
