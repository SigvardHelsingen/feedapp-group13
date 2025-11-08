import asyncio
import logging
from collections import defaultdict

from valkey.asyncio import Valkey
from valkey.asyncio.client import PubSub

from app.db.valkey import PollUpdateEvent, poll_update_topic

logger = logging.getLogger(__name__)


class SSEManager:
    """
    Fans out PollUpdateEvent-s from Valkey to clients for consumption over SSE

    Key ideas:
    - Single shared Valkey pub/sub connection for all poll subscriptions
    - Dynamically (un-)subscribes to topics based on active clients
    - Each client gets an asyncio.Queue with maxsize=1,
        i.e. only latest updates get sent all the way in case of contention
    - Automatically cleans up subscriptions when last client disconnects
    - Configurable connection limits globally and per user
        (TODO: connection limit handling for anonymous users)
    """

    def __init__(
        self,
        valkey_conn_str: str,
        max_connections_per_user: int = 5,
        max_connections_total: int = 1000,
    ):
        self.valkey_conn_str = valkey_conn_str
        self.max_connections_per_user = max_connections_per_user
        self.max_connections_total = max_connections_total

        self.lock = (
            asyncio.Lock()
        )  # For exclusively reading and writing to the state structures
        self.clients: dict[
            int, set[tuple[int | None, asyncio.Queue[PollUpdateEvent]]]
        ] = defaultdict(set)
        self.user_connection_counts: dict[int | None, int] = defaultdict(
            int
        )  # Defaults to 0
        self.subscribed_polls: set[int] = set()

        self.valkey_client: Valkey | None = None
        self.pubsub: PubSub | None = None
        self.ready = False

        self.listener_task: asyncio.Task[None] | None = None

    async def _ensure_connection(self):
        if self.valkey_client is None:
            logger.info("Creating dedicated Valkey client for pubsub")
            self.valkey_client = Valkey.from_url(self.valkey_conn_str)
            self.pubsub = self.valkey_client.pubsub()

            await self.valkey_client.ping()  # Make sure we're connected
            logger.info("Valkey connection established and verified")

            self.ready = True

    async def subscribe(
        self, poll_id: int, user_id: int | None
    ) -> asyncio.Queue[PollUpdateEvent]:
        """
        Subscribe to poll updates
        Returns a queue that will receive PollUpdateEvent-s

        Raises:
            RuntimeError: If connection limits are exceeded
        """
        # only keep the latest update
        client_queue: asyncio.Queue[PollUpdateEvent] = asyncio.Queue(maxsize=1)

        async with self.lock:
            await self._ensure_connection()

            # Check global connection limit
            total_connections = sum(len(clients) for clients in self.clients.values())
            if total_connections >= self.max_connections_total:
                raise RuntimeError(
                    f"Global SSE connection limit reached ({self.max_connections_total})"
                )

            # Check per-user connection limit
            if (
                user_id is not None
                and self.user_connection_counts[user_id]
                >= self.max_connections_per_user
            ):
                raise RuntimeError(
                    f"User SSE connection limit reached ({self.max_connections_per_user})"
                )

            self.clients[poll_id].add((user_id, client_queue))
            self.user_connection_counts[user_id] += 1

            # If this is the first client for this poll, subscribe to the topic
            if poll_id not in self.subscribed_polls:
                topic = poll_update_topic(poll_id)
                await self.pubsub.subscribe(topic)
                self.subscribed_polls.add(poll_id)
                logger.info(f"Subscribed to Redis topic: {topic}")

                # Start the listener task if this is the very first subscription
                # TODO: this might be safe to move
                if self.listener_task is None:
                    self.listener_task = asyncio.create_task(
                        self._listen_to_all_polls()
                    )
                    logger.info("Listener task started")

        logger.info(
            f"User {user_id} subscribed to poll {poll_id} (total clients: {len(self.clients[poll_id])})"
        )
        return client_queue

    async def unsubscribe(
        self,
        poll_id: int,
        user_id: int | None,
        client_queue: asyncio.Queue[PollUpdateEvent],
    ):
        async with self.lock:
            if poll_id in self.clients:
                # Remove the (user_id, queue) tuple
                self.clients[poll_id].discard((user_id, client_queue))
                self.user_connection_counts[user_id] -= 1

                # Clean up user count if it reaches zero
                if self.user_connection_counts[user_id] <= 0:
                    del self.user_connection_counts[user_id]

                # If no more clients for this poll, unsubscribe from the topic
                if not self.clients[poll_id]:
                    if poll_id in self.subscribed_polls:
                        topic = poll_update_topic(poll_id)
                        await self.pubsub.unsubscribe(topic)
                        self.subscribed_polls.discard(poll_id)
                        logger.info(f"Unsubscribed from Redis topic: {topic}")
                    del self.clients[poll_id]

        logger.debug(f"User {user_id} unsubscribed from poll {poll_id}")

    async def _listen_to_all_polls(self):
        """Background task that listens to all subscribed polls on a single connection"""
        if not self.pubsub:
            logger.error("Cannot start listener: pubsub not initialized")
            return

        try:
            logger.info("Starting pubsub listener for all polls")

            while True:
                async with self.lock:
                    has_subscriptions = len(self.subscribed_polls) > 0

                if not has_subscriptions:
                    # No active subscriptions, do not get_message (this would fail)
                    await asyncio.sleep(0.5)
                    continue

                # We have subscriptions, poll for messages
                try:
                    message = await self.pubsub.get_message(
                        ignore_subscribe_messages=False, timeout=1.0
                    )
                except RuntimeError as e:
                    if "pubsub connection not set" in str(e):
                        # unsubscribe raise condition. Ignore and retry
                        await asyncio.sleep(0.1)
                        continue
                    raise

                if message is None:
                    # No message received within timeout
                    continue

                if message["type"] == "message":
                    try:
                        event = PollUpdateEvent.model_validate_json(message["data"])
                        logger.debug(
                            f"Parsed event for poll {event.poll_id} with {len(event.vote_counts)} vote counts"
                        )
                        await self._broadcast_to_clients(event.poll_id, event)
                    except Exception as e:
                        logger.error(f"Error processing message: {e}", exc_info=True)
                elif message["type"] == "subscribe":
                    logger.debug(
                        f"Successfully subscribed to channel: {message['channel']}"
                    )
                elif message["type"] == "unsubscribe":
                    logger.debug(
                        f"Successfully unsubscribed from channel: {message['channel']}"
                    )

        except asyncio.CancelledError:
            logger.info("Pubsub listener task cancelled")
        except Exception as e:
            logger.error(f"Error in pubsub listener task: {e}", exc_info=True)

    async def _broadcast_to_clients(self, poll_id: int, event: PollUpdateEvent):
        """Broadcast an update to all clients subscribed to a poll"""
        async with self.lock:
            clients = self.clients.get(poll_id, set()).copy()

        if not clients:
            logger.debug(f"No clients connected for poll {poll_id}, skipping broadcast")
            return

        logger.debug(f"Broadcasting to {len(clients)} client(s) for poll {poll_id}")

        dead_clients = []
        for user_id, client_queue in clients:
            try:
                # If there's an unpopped event in the queue, just replace it.
                # The client only wants the most recent data anyway
                if client_queue.full():
                    try:
                        client_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass

                client_queue.put_nowait(event)
            except Exception as e:
                logger.warning(f"Failed to send to client for poll {poll_id}: {e}")
                dead_clients.append((user_id, client_queue))

        # Clean up dead clients
        if dead_clients:
            async with self.lock:
                for user_id, dead_client in dead_clients:
                    self.clients[poll_id].discard((user_id, dead_client))
                    self.user_connection_counts[user_id] -= 1
                    if self.user_connection_counts[user_id] <= 0:
                        del self.user_connection_counts[user_id]

    async def shutdown(self):
        """Shutdown all subscriptions and clean up resources"""
        logger.info("Shutting down SSE Manager")

        async with self.lock:
            # Cancel listener task
            if self.listener_task:
                self.listener_task.cancel()
                try:
                    await self.listener_task
                except asyncio.CancelledError:
                    pass
                self.listener_task = None

            # Unsubscribe from all topics
            if self.pubsub:
                for poll_id in list(self.subscribed_polls):
                    topic = poll_update_topic(poll_id)
                    try:
                        await self.pubsub.unsubscribe(topic)
                    except Exception as e:
                        logger.error(f"Error unsubscribing from {topic}: {e}")

                await self.pubsub.aclose()
                self.pubsub = None

            # Close Valkey client
            if self.valkey_client:
                await self.valkey_client.aclose()
                self.valkey_client = None

            self.subscribed_polls.clear()
            self.ready = False

        logger.info("SSE Manager shut down")
