import asyncio
import uuid
import random
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models import DataBreach, BreachSource, User
from app.main import get_password_hash
from app.elasticsearch_client import index_breach

DEMO_DATA = [
    {"title": "LockBit Ransomware: Acme Corp Dump", "description": "Full database dump including 500k customer records, SSNs, and internal emails.", "types": ["financial", "pii", "corporate"], "severity": 95},
    {"title": "Stolen AWS Credentials - Developer Portal", "description": "Leaked AWS access keys and secret keys found on anon paste site. Belongs to FinTech startup.", "types": ["credentials", "corporate"], "severity": 88},
    {"title": "Hospital Patient Records 2026", "description": "Database exported from MedCenter API containing 1.2M patient names, addresses, and medical history.", "types": ["health", "pii"], "severity": 99},
    {"title": "Credit Card Dump - DarkWeb Market", "description": "Batch of 10,000 fresh credit cards with CVV from major retail breach.", "types": ["financial"], "severity": 92},
    {"title": "Source Code Leak - Proprietary Trading Algorithm", "description": "GitHub private repo leaked on Telegram channel containing high-frequency trading bot.", "types": ["corporate", "code"], "severity": 75},
    {"title": "Government Employee Database", "description": "SQL dump containing emails, phone numbers, and hashed passwords of state employees.", "types": ["pii", "credentials", "government"], "severity": 85},
    {"title": "VPN Access Logs & IP Leaks", "description": "Logs exposing real IP addresses of users from a compromised zero-log VPN provider.", "types": ["network", "pii"], "severity": 65},
    {"title": "Crypto Exchange KYC Data", "description": "Passport scans and selfies from a tier-2 cryptocurrency exchange breach.", "types": ["financial", "pii"], "severity": 94},
]

async def seed_data():
    try:
        async with AsyncSessionLocal() as db:
            # 1. Create Admin User if not exists
            result = await db.execute(select(User).where(User.email == 'admin@leakhunter.ai'))
            admin_user = result.scalars().first()
            if not admin_user:
                admin_user = User(
                    email='admin@leakhunter.ai', 
                    hashed_password=get_password_hash('admin123'),
                    is_active=True,
                    role='admin'
                )
                db.add(admin_user)
                await db.commit()
                print("Default admin created: admin@leakhunter.ai / admin123")

            # 2. Check if data breaches already exist
            result = await db.execute(select(DataBreach).limit(1))
            if result.scalars().first():
                print("Demo data already exists. Skipping seed.")
                return

            print("No data found. Seeding demo data...")

            # 3. Create a dummy source
            result = await db.execute(select(BreachSource).where(BreachSource.name == "DarkWeb Intel Source"))
            source = result.scalars().first()
            if not source:
                source = BreachSource(
                    name="DarkWeb Intel Source",
                    url="http://onionlink.mock.onion",
                    source_type="darkweb",
                    reliability_score=90
                )
                db.add(source)
                await db.commit()
                await db.refresh(source)

            now = datetime.utcnow()
            
            # 4. Inject records
            for i in range(45):
                template = random.choice(DEMO_DATA)
                breach = DataBreach(
                    source_id=source.id,
                    title=f"{template['title']} (Batch #{random.randint(1000, 9999)})",
                    description=template['description'],
                    original_url=f"http://{uuid.uuid4().hex[:8]}.onion/leak",
                    severity_score=template['severity'] - random.randint(0, 10),
                    confidence_score=round(random.uniform(0.7, 0.99), 2),
                    data_types=template['types'],
                    discovered_date=now - timedelta(days=random.randint(0, 14)),
                    breach_date=now - timedelta(days=random.randint(0, 20)),
                    record_count=random.randint(1000, 5000000),
                    affected_domains=[f"target-{random.randint(1,100)}.com"],
                    confirmed_authentic=1
                )
                db.add(breach)
                await db.commit()
                await db.refresh(breach)

                # Index to Elasticsearch
                es_doc = {
                    "id": str(breach.id),
                    "title": breach.title,
                    "content": breach.description,
                    "source_id": str(breach.source_id),
                    "source_name": source.name,
                    "severity_score": breach.severity_score,
                    "confidence_score": breach.confidence_score,
                    "data_types": breach.data_types,
                    "discovered_date": breach.discovered_date.isoformat(),
                    "threat_actor": random.choice(["LockBit", "Alphv", "Anonymous", "Unknown"]),
                    "is_verified": True
                }
                try:
                    await index_breach(es_doc)
                except Exception as e:
                    pass
                
            print("Successfully injected 45 demo records into PostgreSQL and Elasticsearch!")
    except Exception as e:
        print(f"Failed to seed data: {e}")

if __name__ == "__main__":
    asyncio.run(seed_data())
