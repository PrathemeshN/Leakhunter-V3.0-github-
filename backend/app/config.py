from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    # Database (TimescaleDB / Postgres)
    DATABASE_URL: str = "postgresql+asyncpg://breach_user:breach_pass@db:5432/leakhunter_v2"
    
    # Redis (for caching, fallback event queue)
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Apache Kafka (for event-driven production queue)
    RABBITMQ_URL: str = "kafka:9092"
    
    # Elasticsearch (for high-performance search indexes)
    ELASTICSEARCH_URL: str = "http://elasticsearch:9200"
    
    # Tor Proxy (for SOCKS5 proxy routing)
    TOR_PROXY_URL: str = "socks5://tor:9050"
    
    # Choice of broker: 'redis' or 'kafka'
    EVENT_BROKER: str = "redis"
    
    # Security / Auth
    SECRET_KEY: str = "your-secret-key-change-in-production-v2-leakhunter"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # OSINT & Verification API keys
    HIBP_API_KEY: Optional[str] = ""
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
