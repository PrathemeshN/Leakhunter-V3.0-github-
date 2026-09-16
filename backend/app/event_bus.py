import json
import logging
import asyncio
from app.config import settings

logger = logging.getLogger(__name__)

# Fallback redis
import redis
redis_client = redis.from_url(settings.REDIS_URL)

try:
    import aio_pika
    RABBITMQ_AVAILABLE = True
except ImportError:
    RABBITMQ_AVAILABLE = False


class EventBus:
    """
    Unified Event Bus abstraction supporting RabbitMQ (Persistent AMQP) and Redis fallback.
    """
    def __init__(self):
        self.broker_type = settings.EVENT_BROKER.lower()
        self.rmq_connection = None
        self.rmq_channel = None
        
    async def connect(self):
        if self.broker_type == "rabbitmq" and RABBITMQ_AVAILABLE:
            try:
                self.rmq_connection = await aio_pika.connect_robust(
                    settings.RABBITMQ_URL,
                    timeout=10
                )
                self.rmq_channel = await self.rmq_connection.channel()
                logger.info("RabbitMQ EventBus initialized successfully.")
            except Exception as e:
                logger.error(f"RabbitMQ connection failed: {e}. Falling back to Redis.")
                self.broker_type = "redis"
        
        if self.broker_type == "redis":
            logger.info("Redis EventBus adapter initialized.")

    async def publish(self, topic: str, message: dict):
        if not self.rmq_channel and self.broker_type == "rabbitmq":
            await self.connect()
            
        try:
            if self.broker_type == "rabbitmq" and self.rmq_channel:
                await self.rmq_channel.default_exchange.publish(
                    aio_pika.Message(body=json.dumps(message).encode()),
                    routing_key=topic
                )
            else:
                redis_client.lpush(topic, json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Failed to publish to topic {topic}: {e}")
            return False

    async def consume(self, topic: str, callback):
        """
        Consumes messages and requires explicit ACK from the callback.
        """
        if not self.rmq_channel and self.broker_type == "rabbitmq":
            await self.connect()
            
        if self.broker_type == "rabbitmq" and self.rmq_channel:
            queue = await self.rmq_channel.declare_queue(topic, durable=True)
            logger.info(f"Subscribed to RabbitMQ queue: {topic}")
            
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process(): # This block auto-ACKs on success, NACKs on exception
                        data = json.loads(message.body.decode())
                        await callback(data)
        else:
            logger.info(f"Subscribed to Redis queue: {topic}")
            while True:
                try:
                    data = redis_client.brpop(topic, timeout=5)
                    if data:
                        payload = json.loads(data[1].decode('utf-8'))
                        await callback(payload)
                except Exception as e:
                    logger.error(f"Redis listen loop error: {e}")
                    await asyncio.sleep(2)

event_bus = EventBus()
