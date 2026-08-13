"""In-memory event bus for real-time admin order notifications.

When a customer's payment is verified and the order is committed,
an event is published here.  The SSE endpoint in admin_routes
waits on this bus instead of polling the database.
"""

import threading
import time
import logging

logger = logging.getLogger(__name__)

# Events older than this are pruned on the next publish.
_MAX_EVENT_AGE_SECONDS = 3600  # 1 hour


class OrderEventBus:
    """Simple thread-safe pub/sub for order events."""

    def __init__(self):
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._events = []

    def publish(self, event_type, order_db_id):
        """Publish a new order event.  Called after payment success + commit."""
        with self._condition:
            now = time.time()
            # Prune old events to prevent unbounded growth.
            self._events = [
                e for e in self._events
                if now - e['timestamp'] < _MAX_EVENT_AGE_SECONDS
            ]
            self._events.append({
                'type': event_type,
                'order_db_id': order_db_id,
                'timestamp': now,
            })
            logger.info(
                'OrderEventBus: published %s for order DB id %s',
                event_type, order_db_id,
            )
            self._condition.notify_all()

    def wait_for_events(self, since_timestamp, timeout=3):
        """Block until a new event arrives or *timeout* expires.

        Returns a list of events whose timestamp is newer than
        *since_timestamp*.  The list may be empty on timeout.
        """
        with self._condition:
            new_events = [
                e for e in self._events
                if e['timestamp'] > since_timestamp
            ]
            if new_events:
                return new_events

            self._condition.wait(timeout=timeout)

            new_events = [
                e for e in self._events
                if e['timestamp'] > since_timestamp
            ]
            return new_events


# Process-wide singleton.
order_event_bus = OrderEventBus()