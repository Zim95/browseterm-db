"""
PostgreSQL LISTEN/NOTIFY listener utility.
Provides synchronous listener for PostgreSQL notifications.
"""

import json
import select
import threading
from typing import Callable, Any, Optional
from dataclasses import dataclass

import psycopg2
import psycopg2.extensions


# Channel names for pg_notify
CONTAINER_STATUS_CHANGE_CHANNEL = "container_status_change"


@dataclass
class ContainerStatusChangePayload:
    """Payload for container status change notifications."""
    id: str
    user_id: str
    name: str
    old_status: str
    new_status: str
    updated_at: str

    @classmethod
    def from_json(cls, payload: str) -> "ContainerStatusChangePayload":
        """Parse JSON payload from pg_notify."""
        data = json.loads(payload)
        return cls(
            id=str(data["id"]),
            user_id=str(data["user_id"]),
            name=data["name"],
            old_status=data["old_status"],
            new_status=data["new_status"],
            updated_at=data["updated_at"]
        )


class PGListener:
    """
    PostgreSQL LISTEN/NOTIFY listener.

    Usage in browseterm-server:

        from browseterm_db.common.pg_listener import (
            PGListener,
            CONTAINER_STATUS_CHANGE_CHANNEL,
            ContainerStatusChangePayload
        )

        def handle_container_status_change(payload: str):
            data = ContainerStatusChangePayload.from_json(payload)
            # Push to SSE clients, update cache, etc.
            print(f"Container {data.id} changed from {data.old_status} to {data.new_status}")

        listener = PGListener(
            host="localhost",
            port=5432,
            user="postgres",
            password="password",
            database="browseterm"
        )

        listener.connect()
        listener.listen(CONTAINER_STATUS_CHANGE_CHANNEL, handle_container_status_change)

        # Block and process notifications (in main thread)
        listener.run()

        # Or run in background thread
        listener.run_in_thread()
    """

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self._conn: Optional[psycopg2.extensions.connection] = None
        self._callbacks: dict[str, Callable[[str], Any]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def connect(self) -> None:
        """Establish connection to PostgreSQL."""
        self._conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database
        )
        self._conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

    def disconnect(self) -> None:
        """Close connection and stop listening."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        if self._conn:
            self._conn.close()
            self._conn = None
        self._callbacks.clear()

    def listen(self, channel: str, callback: Callable[[str], Any]) -> None:
        """
        Subscribe to a PostgreSQL notification channel.

        Args:
            channel: The notification channel name (e.g., 'container_status_change')
            callback: Function to call with the notification payload string
        """
        if not self._conn:
            raise RuntimeError("PGListener not connected. Call connect() first.")

        cursor = self._conn.cursor()
        cursor.execute(f"LISTEN {channel};")
        cursor.close()
        self._callbacks[channel] = callback

    def unlisten(self, channel: str) -> None:
        """Unsubscribe from a PostgreSQL notification channel."""
        if not self._conn:
            return

        if channel in self._callbacks:
            cursor = self._conn.cursor()
            cursor.execute(f"UNLISTEN {channel};")
            cursor.close()
            del self._callbacks[channel]

    def run(self, timeout: float = 5.0) -> None:
        """
        Block and process notifications.

        Args:
            timeout: Select timeout in seconds for checking stop condition
        """
        if not self._conn:
            raise RuntimeError("PGListener not connected. Call connect() first.")

        self._running = True
        while self._running:
            # Use select to wait for notifications with timeout
            if select.select([self._conn], [], [], timeout) == ([], [], []):
                # Timeout, check if we should continue
                continue

            self._conn.poll()
            while self._conn.notifies:
                notify = self._conn.notifies.pop(0)
                if notify.channel in self._callbacks:
                    try:
                        self._callbacks[notify.channel](notify.payload)
                    except Exception as e:
                        print(f"Error in callback for channel {notify.channel}: {e}")

    def run_in_thread(self, timeout: float = 5.0) -> threading.Thread:
        """
        Run the listener in a background thread.

        Args:
            timeout: Select timeout in seconds

        Returns:
            The thread object
        """
        self._thread = threading.Thread(target=self.run, args=(timeout,), daemon=True)
        self._thread.start()
        return self._thread

    def stop(self) -> None:
        """Stop the listener loop."""
        self._running = False

    @property
    def is_connected(self) -> bool:
        """Check if listener is connected."""
        return self._conn is not None and self._conn.closed == 0
