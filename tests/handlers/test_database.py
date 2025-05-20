# UNIT TESTS FOR DATABASE SERVICE HANDLER

import pytest
import psycopg2
from psycopg2 import extras
from unittest.mock import Mock, patch, MagicMock
from src.handlers.database import PostgresRDSHandler


@pytest.fixture
def mock_psycopg2_connect():
    with patch("psycopg2.connect") as mock_connect:
        yield mock_connect


@pytest.fixture
def postgres_handler(mock_psycopg2_connect):
    return PostgresRDSHandler(
        host="test_host",
        port="5432",
        dbname="test_db",
        user="test_user",
        password="test_pass",
        max_retries=3,
        retry_delay=0.1,  # Short delay for testing
    )


class TestPostgresRDSHandler:
    def test_connect_success(self, postgres_handler, mock_psycopg2_connect):
        """Test successful database connection"""
        mock_connection = Mock()
        mock_psycopg2_connect.return_value = mock_connection

        postgres_handler.connect()
        assert postgres_handler.connection is not None
        mock_psycopg2_connect.assert_called_once_with(
            host="test_host",
            port="5432",
            dbname="test_db",
            user="test_user",
            password="test_pass",
            cursor_factory=extras.RealDictCursor,
        )

    def test_connect_failure(self, postgres_handler, mock_psycopg2_connect):
        """Test database connection failure"""
        mock_psycopg2_connect.side_effect = psycopg2.OperationalError(
            "Connection failed"
        )

        postgres_handler.connect()
        assert postgres_handler.connection is None

    @patch.object(PostgresRDSHandler, "check_connection", return_value=True)
    def test_execute_query_success(self, mock_check, postgres_handler):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{"id": 1, "name": "test"}]
        mock_cursor.description = True

        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        postgres_handler.connection = mock_connection

        result = postgres_handler.execute_query("SELECT * FROM test")
        assert result == [{"id": 1, "name": "test"}]
        mock_cursor.execute.assert_called_once_with("SELECT * FROM test", None)

    @patch.object(PostgresRDSHandler, "check_connection", return_value=True)
    def test_execute_query_with_params(self, mock_check, postgres_handler):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{"id": 1}]
        mock_cursor.description = True

        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        postgres_handler.connection = mock_connection

        params = (1, "test")
        postgres_handler.execute_query(
            "SELECT * FROM test WHERE id = %s AND name = %s", params
        )
        mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM test WHERE id = %s AND name = %s", params
        )

    def test_execute_query_no_results(self, postgres_handler):
        """Test query execution with no results"""
        mock_cursor = MagicMock()
        mock_cursor.description = None  # Indicate no results (e.g., INSERT/UPDATE)

        mock_connection = MagicMock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        postgres_handler.connection = mock_connection

        result = postgres_handler.execute_query("INSERT INTO test VALUES (1)")
        assert result == []
        mock_connection.commit.assert_called_once()

    def test_check_connection_reconnect(self, postgres_handler, mock_psycopg2_connect):
        """Test connection health check with reconnection"""
        # Initial connection is None
        assert postgres_handler.connection is None

        # Mock successful connection
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [1]
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_psycopg2_connect.return_value = mock_connection

        result = postgres_handler.check_connection()
        assert result is True
        assert postgres_handler.connection is not None

    def test_check_connection_failure(self, postgres_handler):
        mock_connection = MagicMock()
        mock_connection.cursor.side_effect = psycopg2.OperationalError(
            "Connection lost"
        )

        # Prevent automatic reconnection
        with patch.object(postgres_handler, "connect") as mock_connect:
            mock_connect.side_effect = psycopg2.OperationalError("Reconnect failed")
            postgres_handler.connection = mock_connection

            result = postgres_handler.check_connection()
            assert result is False
            assert postgres_handler.connection is None

    def test_close_connection(self, postgres_handler):
        """Test connection closure"""
        mock_connection = MagicMock()
        postgres_handler.connection = mock_connection

        postgres_handler.close()
        mock_connection.close.assert_called_once()
