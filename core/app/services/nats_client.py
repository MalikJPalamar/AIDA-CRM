"""
AIDA-CRM NATS Client Service
JetStream event publishing and subscription
"""

import asyncio
import json
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import nats
from nats.js import JetStreamContext
from nats.js.api import StreamConfig, ConsumerConfig
import structlog

logger = structlog.get_logger()


class NATSClient:
    """NATS JetStream client for event streaming"""

    def __init__(self, nats_url: str):
        self.nats_url = nats_url
        self.nc: Optional[nats.NATS] = None
        self.js: Optional[JetStreamContext] = None
        self.streams_initialized = False

    async def connect(self):
        """Connect to NATS server"""
        try:
            self.nc = await nats.connect(self.nats_url)
            self.js = self.nc.jetstream()
            logger.info("Connected to NATS", url=self.nats_url)

            # Initialize streams
            await self.initialize_streams()

        except Exception as e:
            logger.error("Failed to connect to NATS", error=str(e), url=self.nats_url)
            raise

    async def disconnect(self):
        """Disconnect from NATS server"""
        if self.nc:
            await self.nc.close()
            logger.info("Disconnected from NATS")

    async def initialize_streams(self):
        """Initialize JetStream streams for CRM events"""
        if self.streams_initialized:
            return

        streams = [
            {
                "name": "CRM_LEADS",
                "subjects": ["leads.captured", "leads.qualified", "leads.rejected", "leads.converted"],
                "description": "Lead lifecycle events"
            },
            {
                "name": "CRM_DEALS",
                "subjects": ["deals.created", "deals.progressed", "deals.won", "deals.lost"],
                "description": "Deal progression events"
            },
            {
                "name": "CRM_COMMS",
                "subjects": ["comms.sent", "comms.opened", "comms.clicked", "comms.replied"],
                "description": "Communication events"
            },
            {
                "name": "CRM_ANALYTICS",
                "subjects": ["analytics.computed", "analytics.alerted", "analytics.report_generated"],
                "description": "Analytics and reporting events"
            }
        ]

        for stream_config in streams:
            try:
                # Check if stream exists
                try:
                    await self.js.stream_info(stream_config["name"])
                    logger.debug("Stream already exists", stream=stream_config["name"])
                except:
                    # Create stream
                    config = StreamConfig(
                        name=stream_config["name"],
                        subjects=stream_config["subjects"],
                        description=stream_config["description"],
                        max_age=7 * 24 * 60 * 60,  # 7 days retention
                        max_bytes=100 * 1024 * 1024,  # 100MB max
                        storage="file"
                    )
                    await self.js.add_stream(config)
                    logger.info("Created stream", stream=stream_config["name"], subjects=stream_config["subjects"])

            except Exception as e:
                logger.error("Failed to initialize stream", stream=stream_config["name"], error=str(e))

        self.streams_initialized = True

    async def publish_event(self, subject: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None):
        """Publish an event to JetStream"""
        try:
            # Prepare event payload
            event_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "data": data
            }

            # Publish to JetStream
            ack = await self.js.publish(
                subject=subject,
                payload=json.dumps(event_data).encode(),
                headers=headers
            )

            logger.info(
                "Event published",
                subject=subject,
                sequence=ack.seq,
                duplicate=ack.duplicate if hasattr(ack, 'duplicate') else False
            )

            return ack

        except Exception as e:
            logger.error("Failed to publish event", subject=subject, error=str(e))
            raise

    async def subscribe_to_events(
        self,
        subject: str,
        handler: Callable[[Dict[str, Any]], None],
        consumer_name: str,
        durable: bool = True
    ):
        """Subscribe to events with a handler function"""
        try:
            async def message_handler(msg):
                try:
                    # Parse event data
                    event_data = json.loads(msg.data.decode())

                    # Call handler
                    await handler(event_data)

                    # Acknowledge message
                    await msg.ack()

                    logger.debug("Event processed", subject=msg.subject, sequence=msg.metadata.sequence.stream)

                except Exception as e:
                    logger.error("Failed to process event", subject=msg.subject, error=str(e))
                    # NAK the message for retry
                    await msg.nak()

            # Create consumer configuration
            consumer_config = ConsumerConfig(
                durable_name=consumer_name if durable else None,
                ack_policy="explicit",
                max_deliver=3,
                ack_wait=30  # 30 seconds
            )

            # Subscribe
            subscription = await self.js.subscribe(
                subject=subject,
                cb=message_handler,
                config=consumer_config
            )

            logger.info("Subscribed to events", subject=subject, consumer=consumer_name)
            return subscription

        except Exception as e:
            logger.error("Failed to subscribe to events", subject=subject, error=str(e))
            raise

    async def get_stream_info(self, stream_name: str) -> Dict[str, Any]:
        """Get information about a stream"""
        try:
            info = await self.js.stream_info(stream_name)
            return {
                "name": info.config.name,
                "subjects": info.config.subjects,
                "messages": info.state.messages,
                "bytes": info.state.bytes,
                "first_seq": info.state.first_seq,
                "last_seq": info.state.last_seq
            }
        except Exception as e:
            logger.error("Failed to get stream info", stream=stream_name, error=str(e))
            return {}

    async def health_check(self) -> bool:
        """Check NATS connection health"""
        try:
            if not self.nc or not self.nc.is_connected:
                return False

            # Test publish/subscribe
            test_subject = "health.check"
            test_data = {"ping": "pong", "timestamp": datetime.utcnow().isoformat()}

            await self.nc.publish(test_subject, json.dumps(test_data).encode())
            return True

        except Exception as e:
            logger.warning("NATS health check failed", error=str(e))
            return False


# Global NATS client instance
nats_client: Optional[NATSClient] = None


async def get_nats_client() -> NATSClient:
    """Get the global NATS client instance"""
    global nats_client
    if nats_client is None:
        raise RuntimeError("NATS client not initialized")
    return nats_client


async def initialize_nats(nats_url: str):
    """Initialize the global NATS client"""
    global nats_client
    nats_client = NATSClient(nats_url)
    await nats_client.connect()


async def close_nats():
    """Close the global NATS client"""
    global nats_client
    if nats_client:
        await nats_client.disconnect()
        nats_client = None