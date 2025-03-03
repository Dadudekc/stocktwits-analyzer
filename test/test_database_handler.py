import pytest
import logging
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure the parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db_handler import DatabaseHandler

@pytest.fixture
def mock_logger():
    """Fixture to create a mock logger."""
    return MagicMock(spec=logging.Logger)

@pytest.fixture
def mock_mysql():
    """Function-scoped fixture to mock MySQL connector in db_handler."""
    # Patch the connector where it is used in db_handler.
    with patch("db_handler.mysql.connector.connect", autospec=False) as mock_connect:
        # Create fresh mock connection and cursor for each test.
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Set up the return values.
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.connection = mock_conn

        # Reset any side effect (so it doesn't carry over from tests that set it).
        mock_connect.side_effect = None

        yield mock_connect, mock_conn, mock_cursor

@pytest.fixture
def db_handler(mock_logger, mock_mysql):
    """Fixture to initialize DatabaseHandler with mocks."""
    # Each test gets its own instance of mock_mysql.
    _, mock_conn, mock_cursor = mock_mysql
    # Instantiate DatabaseHandler; its __init__ will call get_connection(),
    # but our patched connect should return our mock_conn.
    db = DatabaseHandler(mock_logger)
    # Overwrite the connection and cursor after instantiation.
    db.conn = mock_conn
    db.cursor = mock_cursor
    return db, mock_conn, mock_cursor

# ------------------ TESTS ------------------

def test_initialization(db_handler, mock_logger):
    """Test if DatabaseHandler initializes correctly."""
    db, _, _ = db_handler
    mock_logger.info.assert_any_call("✅ Initializing DatabaseHandler for mysql")

def test_get_connection_success(mock_logger, mock_mysql):
    """Test successful database connection."""
    mock_connect, mock_conn, _ = mock_mysql
    db = DatabaseHandler(mock_logger)
    assert db.conn == mock_conn
    mock_logger.info.assert_any_call("✅ Database connection established.")

def test_get_connection_failure(mock_logger, mock_mysql):
    """Test failed database connection."""
    mock_connect, _, _ = mock_mysql
    mock_connect.side_effect = Exception("Connection error")

    with pytest.raises(Exception, match="Connection error"):
        DatabaseHandler(mock_logger)
    
    mock_logger.error.assert_any_call("❌ Failed to connect to MySQL: Connection error")

def test_close_connection(db_handler):
    """Test database connection closing."""
    db, mock_conn, mock_cursor = db_handler
    db.close_connection()

    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

def test_initialize_table(db_handler, mock_logger):
    """Test table initialization query execution."""
    db, _, mock_cursor = db_handler
    db.initialize_table()  # Publicly exposed method now
    mock_cursor.execute.assert_called()
    mock_logger.info.assert_any_call("✅ SentimentData table initialized successfully.")

def test_bulk_insert_sentiment_success(db_handler, mock_logger):
    """Test bulk insert with valid data."""
    db, mock_conn, mock_cursor = db_handler
    test_data = [("AAPL", "2024-03-01 12:00:00", "Good stock", 0.8, 0.7, "positive")]

    db.bulk_insert_sentiment(test_data)

    mock_cursor.executemany.assert_called_once()
    # Allow one or more commit calls:
    assert mock_conn.commit.call_count >= 1
    mock_logger.info.assert_any_call("✅ Bulk insert successful. Inserted 1 records.")

def test_bulk_insert_sentiment_failure(db_handler, mock_logger):
    """Test rollback on bulk insert failure."""
    db, mock_conn, mock_cursor = db_handler
    mock_cursor.executemany.side_effect = Exception("Insert error")

    with pytest.raises(Exception, match="Insert error"):
        db.bulk_insert_sentiment([("AAPL", "2024-03-01 12:00:00", "Good stock", 0.8, 0.7, "positive")])

    mock_conn.rollback.assert_called_once()
    mock_logger.error.assert_any_call("⚠️ Database bulk insert failed: Insert error")

def test_save_sentiment_success(db_handler, mock_logger):
    """Test saving a single sentiment entry."""
    db, mock_conn, mock_cursor = db_handler

    db.save_sentiment("AAPL", "2024-03-01 12:00:00", "Good stock", 0.8, 0.7, "positive")

    # The execute call might be called for table initialization plus the insert;
    # We assert that it is called at least once for the insert.
    assert mock_cursor.execute.call_count >= 1
    assert mock_conn.commit.call_count >= 1
    mock_logger.info.assert_any_call("✅ Saved sentiment data for AAPL.")

def test_save_sentiment_failure(db_handler, mock_logger):
    """Test rollback on failure to save sentiment."""
    db, mock_conn, mock_cursor = db_handler
    mock_cursor.execute.side_effect = Exception("Insert error")

    with pytest.raises(Exception, match="Insert error"):
        db.save_sentiment("AAPL", "2024-03-01 12:00:00", "Good stock", 0.8, 0.7, "positive")

    mock_conn.rollback.assert_called_once()
    mock_logger.error.assert_any_call("⚠️ Error saving sentiment data: Insert error")

def test_fetch_sentiment_success(db_handler, mock_logger):
    """Test fetching sentiment data."""
    db, _, mock_cursor = db_handler
    mock_cursor.fetchall.return_value = [
        ("2024-03-01 12:00:00", "Good stock", 0.8, 0.7, "positive")
    ]

    results = db.fetch_sentiment("AAPL", limit=5)

    # Here, execute may be called for table creation and then for the SELECT.
    assert mock_cursor.execute.call_count >= 1
    assert len(results) == 1
    assert results[0]["content"] == "Good stock"
    assert results[0]["textblob_sentiment"] == 0.8
    assert results[0]["sentiment_category"] == "positive"

def test_fetch_sentiment_failure(db_handler, mock_logger):
    """Test handling of errors in fetching sentiment data."""
    db, _, mock_cursor = db_handler
    mock_cursor.execute.side_effect = Exception("Fetch error")

    results = db.fetch_sentiment("AAPL", limit=5)

    assert results == []
    mock_logger.error.assert_any_call("⚠️ Error fetching sentiment data: Fetch error")
