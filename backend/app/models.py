import uuid
from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, Text, Float, Index, BigInteger
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class DataBreach(Base):
    __tablename__ = "data_breaches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    title = Column(String(512), nullable=False, index=True)
    description = Column(Text, nullable=True)
    breach_date = Column(DateTime(timezone=True), nullable=False, index=True)
    discovered_date = Column(DateTime(timezone=True), server_default=func.now())
    published_date = Column(DateTime(timezone=True), nullable=True)
    
    original_url = Column(String(1024), nullable=True)
    source_reference = Column(String(512), nullable=True)
    
    data_types = Column(ARRAY(String), default=list)
    record_count = Column(BigInteger, nullable=True)
    confirmed_authentic = Column(Integer, default=0)
    confidence_score = Column(Float, default=0.0)
    
    raw_data = Column(JSON, default=dict)
    extracted_samples = Column(JSON, default=list)
    affected_domains = Column(ARRAY(String), default=list)
    affected_countries = Column(ARRAY(String), default=list)
    
    severity_score = Column(Integer, default=0)
    contains_pii = Column(Integer, default=0)
    contains_financial = Column(Integer, default=0)
    contains_credentials = Column(Integer, default=0)
    
    status = Column(String(20), default="active")
    notified_authorities = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ScrapedRecord(Base):
    __tablename__ = "scraped_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    breach_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    data_type = Column(String(50), nullable=False, index=True)
    data_hash = Column(String(64), nullable=False, index=True)
    data_format = Column(String(50))
    domain = Column(String(255), nullable=True, index=True)
    country_code = Column(String(5), nullable=True)
    language = Column(String(10), nullable=True)
    confidence_score = Column(Integer, default=50)
    validation_status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ScraperLog(Base):
    __tablename__ = "scraper_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(String(20), nullable=False)
    records_found = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    errors = Column(JSON, default=list)
    duration_seconds = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="viewer")
    is_active = Column(Boolean, default=False)
    totp_secret = Column(String(32), nullable=True)
    is_totp_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class TelegramChannel(Base):
    __tablename__ = "telegram_channels"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_username = Column(String(255), nullable=False, unique=True)
    channel_title = Column(String(512), nullable=False)
    is_active = Column(Boolean, default=True)
    channel_type = Column(String(50), default="leak_source")
    keyword_mode = Column(String(20), default="high_signal")
    custom_keywords = Column(JSON, default=list)
    reliability_score = Column(Integer, default=50)
    last_scraped_at = Column(DateTime(timezone=True), nullable=True)
    messages_captured = Column(Integer, default=0)
    last_message_id = Column(String(50), nullable=True)
    breach_source_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ForumIdentity(Base):
    __tablename__ = 'forum_identities'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ForumMirror(Base):
    __tablename__ = 'forum_mirrors'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    forum_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    onion_url = Column(String(1024), nullable=False, unique=True)
    is_online = Column(Boolean, default=False)
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    consecutive_failures = Column(Integer, default=0)
    discovery_source = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ForumAccount(Base):
    __tablename__ = 'forum_accounts'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    forum_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    username = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    session_cookies = Column(JSON, nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_scrape_at = Column(DateTime(timezone=True), nullable=True)
    posts_scraped = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AlertRule(Base):
    __tablename__ = 'alert_rules'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    min_severity = Column(Integer, default=0)
    target_keywords = Column(ARRAY(String), default=list)
    target_data_types = Column(ARRAY(String), default=list)
    destination_type = Column(String(50), nullable=False)
    destination_url = Column(String(1024), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AlertLog(Base):
    __tablename__ = 'alert_logs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    breach_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    error_message = Column(Text, nullable=True)
    dispatched_at = Column(DateTime(timezone=True), server_default=func.now())
class BreachSource(Base):
    __tablename__ = 'breach_sources'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=True)
    source_type = Column(String(50), nullable=False)  # forum, pastebin, telegram, darkweb
    reliability_score = Column(Integer, default=50)   # 0-100
    is_active = Column(Integer, default=1)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
