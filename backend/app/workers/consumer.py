import asyncio
import json
import logging
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("leakhunter_consumer")

from app.event_bus import event_bus
from app.database import AsyncSessionLocal
from app.models import DataBreach, ScrapedRecord, ScraperLog
from app.pipeline.preprocessing import compute_content_hash, extract_domains_from_text
from app.pipeline.extractor import run_extraction_pipeline
from app.pipeline.classifier import predict_leak_type
from app.pipeline.verifier import verify_leak_authenticity, calculate_confidence_score
from app.pipeline.traceback import run_traceback_analysis
from app.elasticsearch_client import index_breach

# Import redis to publish processed notifications to WebSocket channels
import redis
from app.config import settings
redis_client = redis.from_url(settings.REDIS_URL)


async def process_raw_leak(event: dict):
    """
    Subscribes to raw leak messages, runs the full analysis pipeline, 
    persists findings in TimescaleDB, indexes in Elasticsearch, and triggers alerts.
    """
    source_id = event.get("source_id")
    title = event.get("title", "Unknown Data Leak")
    raw_content = event.get("raw_content", "")
    original_url = event.get("original_url", "")
    source_ref = event.get("source_reference", "")
    breach_date_str = event.get("breach_date")
    
    if not raw_content:
        logger.warning("Empty leak content received, ignoring event.")
        return
        
    breach_date = datetime.utcnow()
    if breach_date_str:
        try:
            breach_date = datetime.fromisoformat(breach_date_str.replace("Z", "+00:00"))
        except Exception:
            pass
            
    # Step 1: Preprocessing & Content Hash Deduplication
    content_hash = compute_content_hash(raw_content)
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        # Check if record has already been scraped/processed (Deduplication)
        dup_check = await session.execute(
            select(ScrapedRecord).where(ScrapedRecord.data_hash == content_hash)
        )
        if dup_check.scalars().first():
            logger.info(f"Duplicate leak detected (hash: {content_hash}). Skipping processing.")
            return

        logger.info(f"Start processing new data leak: '{title}'")
        
        # Step 2: Extraction (Regex + spaCy NER)
        extracted_pii = run_extraction_pipeline(raw_content)
        
        # Determine unique affected domains and countries
        domains = extract_domains_from_text(raw_content)
        countries = extracted_pii.get("affected_countries", [])
        
        # Step 3: Classification (scikit-learn pipeline)
        ml_prediction = predict_leak_type(raw_content)
        category = ml_prediction["category"]
        severity_score = ml_prediction["severity_score"]
        confidence = ml_prediction["confidence"]
        
        # Determine classification flags
        contains_pii = 1 if any(k in extracted_pii for k in ["aadhaar_card", "pan_card", "ssn", "phone", "person_names"]) else 0
        contains_financial = 1 if any(k in extracted_pii for k in ["credit_card", "financial"]) else 0
        contains_credentials = 1 if "email" in extracted_pii or "password" in extracted_pii or category == "credentials" else 0
        
        # Step 4: Verification (HaveIBeenPwned & vendor simulator)
        verified_status = await verify_leak_authenticity(
            emails=extracted_pii.get("email", []),
            domains=domains,
            category=ml_prediction
        )
        
        # Step 4.5: Calculate Confidence Score based on source credibility and proofs
        confidence = calculate_confidence_score(
            source_reference=source_ref,
            raw_content=raw_content,
            confirmed_authentic=verified_status,
            data_types=data_types_list
        )
        
        # Step 5: Traceback OSINT Analysis
        traceback_data = await run_traceback_analysis(domains, raw_content)
        
        # Construct DB Breach Record
        new_breach = DataBreach(
            id=breach_uuid,
            source_id=uuid.UUID(source_id) if source_id else uuid.uuid4(),
            title=title,
            description=event.get("description", f"Scraped from {original_url}"),
            breach_date=breach_date,
            original_url=original_url,
            source_reference=source_ref,
            data_types=data_types_list,
            record_count=event.get("record_count", len(extracted_pii.get("email", [])) or 1),
            confirmed_authentic=verified_status,
            confidence_score=confidence,
            raw_data={
                "extracted_pii": extracted_pii,
                "traceback": traceback_data,
                "classification": ml_prediction
            },
            extracted_samples=extracted_pii.get("email", [])[:10], # Keep a few non-sensitive samples for verification
            affected_domains=domains,
            affected_countries=countries,
            severity_score=severity_score,
            contains_pii=contains_pii,
            contains_financial=contains_financial,
            contains_credentials=contains_credentials,
            status="active"
        )
        
        session.add(new_breach)
        
        # Save content hash for future deduplication
        new_scraped_record = ScrapedRecord(
            breach_id=breach_uuid,
            data_type=category,
            data_hash=content_hash,
            data_format="plaintext",
            confidence_score=int(confidence * 100)
        )
        session.add(new_scraped_record)
        
        await session.commit()
        logger.info(f"Saved breach to TimescaleDB (UUID: {breach_uuid})")
        
        # Step 6: Index in Elasticsearch
        es_doc = {
            "source_id": source_id,
            "title": title,
            "description": event.get("description", ""),
            "breach_date": breach_date.isoformat(),
            "discovered_date": datetime.utcnow().isoformat(),
            "data_types": data_types_list,
            "record_count": new_breach.record_count,
            "severity_score": severity_score,
            "original_url": original_url,
            "affected_domains": domains,
            "affected_countries": countries,
            "raw_content": raw_content[:10000],  # Limit size of full-text index
            "status": "active"
        }
        await index_breach(str(breach_uuid), es_doc)
        logger.info(f"Indexed breach in Elasticsearch: {breach_uuid}")
        
        # Step 7: Push Real-Time Alert to WebSocket Channel
        websocket_alert = {
            "event": "new_breach",
            "data": {
                "id": str(breach_uuid),
                "title": title,
                "severity_score": severity_score,
                "category": category,
                "record_count": new_breach.record_count,
                "affected_domains": domains,
                "discovered_date": datetime.utcnow().isoformat()
            }
        }
        try:
            redis_client.publish("threat_alerts", json.dumps(websocket_alert))
            logger.info(f"Published real-time WebSocket alert for: {title}")
        except Exception as ws_err:
            logger.warning(f"Could not publish WebSocket alert (Redis offline): {ws_err}")


async def async_listening_loop():
    logger.info("Initializing LeakHunter V3 RabbitMQ Consumer Pipeline...")
    await event_bus.connect()
    
    # event_bus.consume takes a callback and auto-ACKs on success
    await event_bus.consume("raw-leaks", process_raw_leak)

def run_listening_loop():
    asyncio.run(async_listening_loop())

if __name__ == "__main__":
    run_listening_loop()
