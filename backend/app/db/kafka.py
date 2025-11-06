from collections.abc import Generator
from typing import Annotated

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from fastapi import Depends, Request
from pydantic import BaseModel

from app.config import Settings

VOTE_EVENT_TOPIC = "vote-event"


class VoteEvent(BaseModel):
    user_id: int
    poll_option_id: int


async def create_kafka_producer(settings: Settings):
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        key_serializer=_serialize_key,
        value_serializer=_serialize_value,
    )
    await producer.start()
    return producer


def _get_kafka_producer(request: Request) -> Generator[AIOKafkaProducer, None]:
    yield request.app.state.kafka_producer


# Injectable dependency for our routes
KafkaProducer = Annotated[AIOKafkaProducer, Depends(_get_kafka_producer)]


async def create_kafka_consumer(settings: Settings):
    """
    Create a Kafka consumer, configured in such a way that every message
    will be consumed **at least once**.

    TODO: one consumer process per partition
    """
    consumer = AIOKafkaConsumer(
        VOTE_EVENT_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="vote-event-processor",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        auto_commit_interval_ms=5000,
        key_deserializer=_deserialize_key,
        value_deserializer=_deserialize_value,
    )
    await consumer.start()
    return consumer


def _serialize_key(k: int) -> bytes:
    """Serialize topic key (poll_id: int)"""
    return str(k).encode()


def _deserialize_key(k: bytes) -> int:
    """Deserialize topic key (poll_id: int)"""
    return int(k.decode())


# TODO: should we do this in a more efficient format?
def _serialize_value(x: VoteEvent) -> bytes:
    return x.model_dump_json().encode()


def _deserialize_value(x: bytes) -> VoteEvent:
    return VoteEvent.model_validate_json(x.decode())
