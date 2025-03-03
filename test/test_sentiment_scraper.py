import os
import time
import json
import tempfile
import shutil
import asyncio
import pytest
from datetime import datetime, timedelta
from pathlib import Path
import re

# Import the module to be tested
from sentiment_scraper import (
    get_ephemeral_driver,
    load_cookies,
    get_stocktwits_url,
    clean_text,
    analyze_sentiments_advanced,
    is_spam,
    scroll_and_collect,
    extract_messages,
    append_to_csv_by_ticker_and_sentiment,
    bulk_save_sentiment,
    cleanup_old_files,
    parse_timestamp,
    single_ticker_scrape,
    run_multi_ticker_scraper,
    logger  # for checking log outputs if needed
)

# We'll need to patch Selenium and DatabaseHandler calls for tests that involve side effects.
from unittest.mock import MagicMock, patch

# ------------------ Fixtures ------------------

@pytest.fixture
def fake_driver():
    """Return a fake Selenium driver with scripted behavior for scrolling."""
    driver = MagicMock()
    # Simulate a page that has a fixed scroll height.
    driver.execute_script.side_effect = lambda script: 1000 if "document.body.scrollHeight" in script else None
    return driver

@pytest.fixture
def temp_cookie_file(tmp_path):
    """Creates a temporary cookie file and returns its path."""
    cookie_file = tmp_path / "stocktwits_cookies.json"
    cookies = [{"name": "session", "value": "dummy", "sameSite": "Lax"}]
    cookie_file.write_text(json.dumps(cookies))
    # Temporarily change the COOKIE_FILE constant in the module
    original = os.path.exists("stocktwits_cookies.json")
    if original:
        os.rename("stocktwits_cookies.json", "stocktwits_cookies_backup.json")
    shutil.copy(cookie_file, "stocktwits_cookies.json")
    yield "stocktwits_cookies.json"
    os.remove("stocktwits_cookies.json")
    if original:
        os.rename("stocktwits_cookies_backup.json", "stocktwits_cookies.json")

# ------------------ Tests ------------------

def test_get_stocktwits_url():
    ticker = "AAPL"
    url = get_stocktwits_url(ticker)
    assert "AAPL" in url
    assert url.startswith("https://stocktwits.com/symbol/")

def test_clean_text():
    raw = "Check this out: http://example.com!   Extra  spaces, and symbols #@!"
    cleaned = clean_text(raw)
    # Expect URLs removed, punctuation gone, and extra spaces trimmed.
    assert "http" not in cleaned
    assert "  " not in cleaned

def test_analyze_sentiments_advanced():
    # Use a simple positive and negative phrase
    positive_text = "I love this stock!"
    tb_score, vd_score, final_score, category = analyze_sentiments_advanced(positive_text)
    # The category should be Bullish if final_score > 0.2.
    assert category in ["Bullish", "Neutral", "Bearish"]
    # Not asserting exact values since TextBlob/VADER scores can vary.

def test_parse_timestamp():
    iso_str = "2025-02-27T08:36:59Z"
    parsed = parse_timestamp(iso_str)
    # Check format YYYY-MM-DD HH:MM:SS
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", parsed)

def test_is_spam():
    # Reset globals to ensure clean state
    from sentiment_scraper import recent_messages, message_list, spam_reset_time
    recent_messages.clear()
    message_list.clear()
    # A short message should not be considered spam.
    assert not is_spam("Hi")
    # Add a message and check for similar spam.
    msg = "This is a test message"
    assert not is_spam(msg)
    # A very similar message should be flagged as spam.
    assert is_spam("This is a test message.")

def test_scroll_and_collect(fake_driver):
    # Ensure that scrolling returns some output (we simulate a constant height)
    fake_driver.execute_script.side_effect = lambda script: 1000 if "document.body.scrollHeight" in script else None
    html = "<html><body>Test</body></html>"
    fake_driver.page_source = html
    result = scroll_and_collect(fake_driver)
    assert result == html

def test_extract_messages():
    # Create a small HTML snippet with two message blocks.
    html = """
    <html>
      <body>
        <time datetime="2025-02-27T08:36:59Z"></time>
        <div class="RichTextMessage_body__4qUeP">Message One</div>
        <time datetime="2025-02-27T09:00:00Z"></time>
        <div class="RichTextMessage_body__4qUeP">Message Two</div>
      </body>
    </html>
    """
    messages = extract_messages(html)
    assert len(messages) == 2
    for m in messages:
        assert "timestamp" in m and "content" in m

def test_append_to_csv_by_ticker_and_sentiment(tmp_path):
    # Use temporary directory for CSV outputs.
    test_dir = tmp_path / "AAPL"
    test_dir.mkdir()
    sample_data = [{
        "ticker": "AAPL",
        "sentiment_category": "Bullish",
        "text": "Test",
        "timestamp": "2025-02-27 08:36:59",
        "textblob_sentiment_tb": 0.1,
        "textblob_sentiment_vader": 0.2
    }]
    # Override BASE_DATA_DIR to use temp directory.
    from sentiment_scraper import BASE_DATA_DIR
    original_base = BASE_DATA_DIR
    try:
        # Set to temp path
        import sentiment_scraper
        sentiment_scraper.BASE_DATA_DIR = tmp_path
        append_to_csv_by_ticker_and_sentiment(sample_data)
        # Check file exists
        csv_file = tmp_path / "AAPL" / "AAPL_Bullish_sentiment.csv"
        assert csv_file.exists()
        df = __import__("pandas").read_csv(csv_file)
        assert not df.empty
    finally:
        sentiment_scraper.BASE_DATA_DIR = original_base

def test_bulk_save_sentiment(monkeypatch):
    # Create a fake DatabaseHandler with a dummy bulk_insert_sentiment method.
    class FakeDB:
        def bulk_insert_sentiment(self, data):
            self.data = data
    fake_db = FakeDB()
    monkeypatch.setattr("sentiment_scraper.db", fake_db)
    sample_data = [{
        "ticker": "AAPL",
        "timestamp": "2025-02-27 08:36:59",
        "text": "Test",
        "textblob_sentiment_tb": 0.1,
        "textblob_sentiment_vader": 0.2,
        "sentiment_category": "Bullish"
    }]
    bulk_save_sentiment(sample_data)
    assert hasattr(fake_db, "data")
    assert len(fake_db.data) == 1

def test_cleanup_old_files(tmp_path):
    # Create dummy CSV file with an old timestamp in the filename.
    ticker = "AAPL"
    ticker_dir = tmp_path / ticker
    ticker_dir.mkdir()
    old_time = (datetime.now() - timedelta(days=8)).strftime("%Y%m%d_%H%M%S")
    filename = f"{ticker}_sentiment_{old_time}.csv"
    file_path = ticker_dir / filename
    file_path.write_text("dummy")
    # Override BASE_DATA_DIR in module.
    from sentiment_scraper import BASE_DATA_DIR
    original_base = BASE_DATA_DIR
    try:
        import sentiment_scraper
        sentiment_scraper.BASE_DATA_DIR = tmp_path
        cleanup_old_files(ticker, days=7)
        assert not file_path.exists()
    finally:
        sentiment_scraper.BASE_DATA_DIR = original_base

def test_single_ticker_scrape(monkeypatch):
    # Patch out functions that do network and Selenium work.
    fake_summary = "Test Summary"
    fake_processed = [{"ticker": "AAPL", "sentiment_category": "Bullish", "text": "Test", "timestamp": "2025-02-27 08:36:59",
                        "textblob_sentiment_tb": 0.1, "textblob_sentiment_vader": 0.2}]
    monkeypatch.setattr("sentiment_scraper.get_ephemeral_driver", lambda: MagicMock())
    monkeypatch.setattr("sentiment_scraper.load_cookies", lambda driver: False)
    monkeypatch.setattr("sentiment_scraper.scroll_and_collect", lambda driver: "<html></html>")
    monkeypatch.setattr("sentiment_scraper.extract_messages", lambda html: [{
        "timestamp": "2025-02-27T08:36:59Z",
        "content": "Test message"
    }])
    monkeypatch.setattr("sentiment_scraper.analyze_sentiments_advanced", lambda text: (0.1, 0.2, 0.3, "Bullish"))
    # Patch bulk_save and CSV functions to do nothing.
    monkeypatch.setattr("sentiment_scraper.bulk_save_sentiment", lambda data: None)
    monkeypatch.setattr("sentiment_scraper.append_to_csv_by_ticker_and_sentiment", lambda data: None)
    monkeypatch.setattr("sentiment_scraper.cleanup_old_files", lambda ticker, days=7: None)
    summary, processed = single_ticker_scrape("AAPL")
    assert "AAPL" in summary
    assert isinstance(processed, list)
    # At least one message should be processed.
    assert len(processed) >= 1

@pytest.mark.asyncio
async def test_run_multi_ticker_scraper(monkeypatch):
    # Patch single_ticker_scrape to return a fixed summary and data.
    async def fake_to_thread(func, ticker):
        return ("Fake Summary", [{"ticker": ticker, "sentiment_category": "Bullish", "text": "Test",
                                  "timestamp": "2025-02-27 08:36:59", "textblob_sentiment_tb": 0.1,
                                  "textblob_sentiment_vader": 0.2}])
    monkeypatch.setattr("asyncio.to_thread", fake_to_thread)
    # Run the async generator for one iteration.
    gen = run_multi_ticker_scraper(tickers=["AAPL"], interval_minutes=0, run_duration_hours=0.001)
    embeds = []
    async for embed in gen:
        embeds.append(embed)
    # Ensure we get at least one embed.
    assert len(embeds) >= 1
