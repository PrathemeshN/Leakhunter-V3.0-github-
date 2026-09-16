import asyncio
import json
import logging
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import AlertRule, AlertLog
from app.event_bus import redis_client
from app.alerts.dispatcher import dispatch_webhook

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("alert_worker")

async def evaluate_and_dispatch(alert_data: dict):
    """
    Evaluates incoming alert against all active rules and dispatches if criteria met.
    """
    async with AsyncSessionLocal() as db:
        # Fetch all active rules
        result = await db.execute(select(AlertRule).where(AlertRule.is_active == True))
        rules = result.scalars().all()
        
        breach_severity = alert_data.get("severity", 0)
        breach_data_types = alert_data.get("data_types", [])
        
        # Combine title and desc for keyword matching
        text_corpus = f"{alert_data.get('title', '')} {alert_data.get('description', '')}".lower()
        
        for rule in rules:
            # Check 1: Minimum Severity
            if rule.min_severity > 0 and breach_severity < rule.min_severity:
                continue
                
            # Check 2: Target Keywords (if any defined)
            if rule.target_keywords:
                matched_kw = False
                for kw in rule.target_keywords:
                    if kw.lower() in text_corpus:
                        matched_kw = True
                        break
                if not matched_kw:
                    continue
                    
            # Check 3: Target Data Types (if any defined)
            if rule.target_data_types:
                matched_dt = False
                for dt in rule.target_data_types:
                    if dt in breach_data_types:
                        matched_dt = True
                        break
                if not matched_dt:
                    continue
            
            # Rule matches! Dispatch Webhook
            logger.info(f"Rule '{rule.name}' matched breach '{alert_data.get('title')[:30]}'. Dispatching to {rule.destination_type}.")
            
            success = await dispatch_webhook(
                alert_data=alert_data,
                destination_type=rule.destination_type,
                webhook_url=rule.destination_url
            )
            
            # Note: alert_data might not have 'id' if it's purely a websocket payload. 
            # We assume consumer passed breach_id in payload.
            breach_id_str = alert_data.get("id") or alert_data.get("breach_id")
            
            # Try to log to DB (best effort, ignore missing UUID issues for now if missing)
            if breach_id_str:
                try:
                    alert_log = AlertLog(
                        rule_id=rule.id,
                        breach_id=breach_id_str,
                        status="success" if success else "failed",
                        error_message=None if success else "Webhook dispatch failed. Check logs."
                    )
                    db.add(alert_log)
                    await db.commit()
                except Exception as db_err:
                    logger.error(f"Failed to save AlertLog: {db_err}")


async def alert_listener_loop():
    """
    Subscribes to Redis 'threat_alerts' pubsub channel and processes incoming leaks.
    """
    logger.info("Alert Worker started. Connecting to Redis pubsub...")
    pubsub = redis_client.pubsub()
    pubsub.subscribe("threat_alerts")
    
    logger.info("Listening for high-severity threats on 'threat_alerts' channel...")
    
    try:
        while True:
            # Poll for messages
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                try:
                    payload = json.loads(message['data'].decode('utf-8'))
                    logger.info(f"Received alert event: {payload.get('title', 'Unknown Title')[:50]}...")
                    await evaluate_and_dispatch(payload)
                except Exception as e:
                    logger.error(f"Error processing alert message: {e}")
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        logger.info("Alert Worker shutting down...")
    finally:
        pubsub.unsubscribe("threat_alerts")

if __name__ == "__main__":
    asyncio.run(alert_listener_loop())
