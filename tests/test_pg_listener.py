"""
Tests for PGListener - PostgreSQL LISTEN/NOTIFY utility
"""

# builtins
import os
import json
import threading
import time
from unittest import TestCase
from unittest.mock import MagicMock, patch

# third party
from dotenv import load_dotenv

# local
from browseterm_db.common.config import DBConfig
from browseterm_db.migrations.migrator import Migrator
from browseterm_db.common.config import TEST_MIGRATIONS_DIR
from browseterm_db.common.pg_listener import (
    PGListener,
    ContainerStatusChangePayload,
    CONTAINER_STATUS_CHANGE_CHANNEL
)


load_dotenv('.env')


class TestContainerStatusChangePayload(TestCase):
    """
    Tests for ContainerStatusChangePayload dataclass
    """

    def test_1_from_json_valid_payload(self) -> None:
        """
        Test parsing a valid JSON payload
        """
        print('test_1_from_json_valid_payload: ', end="")
        payload_dict = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "987e6543-e21b-12d3-a456-426614174000",
            "name": "test-container",
            "old_status": "Pending",
            "new_status": "Running",
            "updated_at": "2025-12-15T10:30:00"
        }
        payload_json = json.dumps(payload_dict)

        result = ContainerStatusChangePayload.from_json(payload_json)

        self.assertEqual(result.id, payload_dict["id"])
        self.assertEqual(result.user_id, payload_dict["user_id"])
        self.assertEqual(result.name, payload_dict["name"])
        self.assertEqual(result.old_status, payload_dict["old_status"])
        self.assertEqual(result.new_status, payload_dict["new_status"])
        self.assertEqual(result.updated_at, payload_dict["updated_at"])
        print('OK')

    def test_2_from_json_with_uuid_objects(self) -> None:
        """
        Test parsing payload where UUIDs might be represented differently
        """
        print('test_2_from_json_with_uuid_objects: ', end="")
        payload_dict = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "987e6543-e21b-12d3-a456-426614174000",
            "name": "my-container",
            "old_status": "Running",
            "new_status": "Failed",
            "updated_at": "2025-12-15T12:00:00"
        }
        payload_json = json.dumps(payload_dict)

        result = ContainerStatusChangePayload.from_json(payload_json)

        # UUIDs should be converted to strings
        self.assertIsInstance(result.id, str)
        self.assertIsInstance(result.user_id, str)
        print('OK')

    def test_3_channel_constant_value(self) -> None:
        """
        Test that the channel constant has the expected value
        """
        print('test_3_channel_constant_value: ', end="")
        self.assertEqual(CONTAINER_STATUS_CHANGE_CHANNEL, "container_status_change")
        print('OK')


class TestPGListenerUnit(TestCase):
    """
    Unit tests for PGListener (mocked database)
    """

    def test_1_listener_initialization(self) -> None:
        """
        Test PGListener initializes with correct attributes
        """
        print('test_1_listener_initialization: ', end="")
        listener = PGListener(
            host="localhost",
            port=5432,
            user="testuser",
            password="testpass",
            database="testdb"
        )

        self.assertEqual(listener.host, "localhost")
        self.assertEqual(listener.port, 5432)
        self.assertEqual(listener.user, "testuser")
        self.assertEqual(listener.password, "testpass")
        self.assertEqual(listener.database, "testdb")
        self.assertFalse(listener.is_connected)
        print('OK')

    def test_2_listen_without_connect_raises_error(self) -> None:
        """
        Test that calling listen() without connect() raises RuntimeError
        """
        print('test_2_listen_without_connect_raises_error: ', end="")
        listener = PGListener(
            host="localhost",
            port=5432,
            user="testuser",
            password="testpass",
            database="testdb"
        )

        with self.assertRaises(RuntimeError) as context:
            listener.listen("test_channel", lambda x: x)

        self.assertIn("not connected", str(context.exception))
        print('OK')

    def test_3_run_without_connect_raises_error(self) -> None:
        """
        Test that calling run() without connect() raises RuntimeError
        """
        print('test_3_run_without_connect_raises_error: ', end="")
        listener = PGListener(
            host="localhost",
            port=5432,
            user="testuser",
            password="testpass",
            database="testdb"
        )

        with self.assertRaises(RuntimeError) as context:
            listener.run()

        self.assertIn("not connected", str(context.exception))
        print('OK')

    @patch('browseterm_db.common.pg_listener.psycopg2')
    def test_4_connect_creates_connection(self, mock_psycopg2) -> None:
        """
        Test that connect() creates a database connection
        """
        print('test_4_connect_creates_connection: ', end="")
        mock_conn = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn

        listener = PGListener(
            host="localhost",
            port=5432,
            user="testuser",
            password="testpass",
            database="testdb"
        )
        listener.connect()

        mock_psycopg2.connect.assert_called_once_with(
            host="localhost",
            port=5432,
            user="testuser",
            password="testpass",
            database="testdb"
        )
        mock_conn.set_isolation_level.assert_called_once()
        print('OK')

    @patch('browseterm_db.common.pg_listener.psycopg2')
    def test_5_listen_executes_listen_command(self, mock_psycopg2) -> None:
        """
        Test that listen() executes LISTEN SQL command
        """
        print('test_5_listen_executes_listen_command: ', end="")
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_psycopg2.connect.return_value = mock_conn

        listener = PGListener(
            host="localhost",
            port=5432,
            user="testuser",
            password="testpass",
            database="testdb"
        )
        listener.connect()
        listener.listen("test_channel", lambda x: x)

        mock_cursor.execute.assert_called_with("LISTEN test_channel;")
        mock_cursor.close.assert_called_once()
        print('OK')

    @patch('browseterm_db.common.pg_listener.psycopg2')
    def test_6_disconnect_closes_connection(self, mock_psycopg2) -> None:
        """
        Test that disconnect() closes the connection
        """
        print('test_6_disconnect_closes_connection: ', end="")
        mock_conn = MagicMock()
        mock_conn.closed = 0  # 0 means connection is open
        mock_psycopg2.connect.return_value = mock_conn

        listener = PGListener(
            host="localhost",
            port=5432,
            user="testuser",
            password="testpass",
            database="testdb"
        )
        listener.connect()
        listener.disconnect()

        mock_conn.close.assert_called_once()
        print('OK')

    @patch('browseterm_db.common.pg_listener.psycopg2')
    def test_7_stop_sets_running_to_false(self, mock_psycopg2) -> None:
        """
        Test that stop() sets _running to False
        """
        print('test_7_stop_sets_running_to_false: ', end="")
        mock_conn = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn

        listener = PGListener(
            host="localhost",
            port=5432,
            user="testuser",
            password="testpass",
            database="testdb"
        )
        listener.connect()
        listener._running = True
        listener.stop()

        self.assertFalse(listener._running)
        print('OK')


class TestPGListenerIntegration(TestCase):
    """
    Integration tests for PGListener with real database
    These tests require a running PostgreSQL instance
    """

    def setUp(self) -> None:
        self.db_config: DBConfig = DBConfig(
            username=os.getenv('TEST_DB_USERNAME'),
            password=os.getenv('TEST_DB_PASSWORD'),
            host=os.getenv('TEST_DB_HOST'),
            port=int(os.getenv('TEST_DB_PORT')),
            database=os.getenv('TEST_DB_DATABASE')
        )

    def test_1_connect_and_disconnect(self) -> None:
        """
        Test real connection to PostgreSQL
        """
        print('test_1_connect_and_disconnect: ', end="")
        listener = PGListener(
            host=self.db_config.host,
            port=self.db_config.port,
            user=self.db_config.username,
            password=self.db_config.password,
            database=self.db_config.database
        )

        listener.connect()
        self.assertTrue(listener.is_connected)

        listener.disconnect()
        self.assertFalse(listener.is_connected)
        print('OK')

    def test_2_listen_to_channel(self) -> None:
        """
        Test subscribing to a notification channel
        """
        print('test_2_listen_to_channel: ', end="")
        listener = PGListener(
            host=self.db_config.host,
            port=self.db_config.port,
            user=self.db_config.username,
            password=self.db_config.password,
            database=self.db_config.database
        )

        received_payloads = []

        def callback(payload: str):
            received_payloads.append(payload)

        listener.connect()
        listener.listen("test_channel", callback)

        # Verify the callback is registered
        self.assertIn("test_channel", listener._callbacks)

        listener.disconnect()
        print('OK')

    def test_3_run_in_thread(self) -> None:
        """
        Test running listener in background thread
        """
        print('test_3_run_in_thread: ', end="")
        listener = PGListener(
            host=self.db_config.host,
            port=self.db_config.port,
            user=self.db_config.username,
            password=self.db_config.password,
            database=self.db_config.database
        )

        listener.connect()
        listener.listen("test_channel", lambda x: x)

        thread = listener.run_in_thread(timeout=1.0)
        self.assertTrue(thread.is_alive())

        # Stop the listener
        listener.stop()
        time.sleep(1.5)  # Wait for thread to finish

        listener.disconnect()
        print('OK')
