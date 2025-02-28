import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import time
import json
import re
import logging
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import discord

# Selenium and Web Scraping
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from selenium.common.exceptions import WebDriverException

# Sentiment Analysis
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from difflib import SequenceMatcher

# Database Integration
from db_handler import DatabaseHandler


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SentimentScraper")

# -------------------------------------------------------------------------
# Constants & Files
COOKIE_FILE = "stocktwits_cookies.json"
MAX_SCROLLS = 15
SCROLL_PAUSE = 2
SPAM_THRESHOLD = 0.85
MAX_SPAM_MESSAGES = 100
SPAM_RESET_HOURS = 24  # reset spam detection daily

BASE_DATA_DIR = Path(r"D:\SocialMediaManager\data")
BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------------
# Global Variables
db = DatabaseHandler(logger)
recent_messages = set()
message_list = []
spam_reset_time = datetime.now() + timedelta(hours=SPAM_RESET_HOURS)

# -------------------------------------------------------------------------
def get_ephemeral_driver():
    """
    Creates a brand new Selenium driver for a single ticker scrape,
    guaranteeing no 'invalid session id' across tickers.
    """
    logger.info("🌐 Creating ephemeral Selenium driver session for one ticker.")
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-extensions")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("log-level=3")

    driver_path = ChromeDriverManager().install()
    driver = webdriver.Chrome(service=ChromeService(driver_path), options=options)
    return driver

def load_cookies(driver):
    """
    Loads Stocktwits cookies from file if available, then sets them in the browser.
    """
    if not os.path.exists(COOKIE_FILE):
        return False
    try:
        with open(COOKIE_FILE, "r") as f:
            cookies = json.load(f)
        for cookie in cookies:
            cookie.pop("sameSite", None)
            driver.add_cookie(cookie)
        logger.info("✅ Cookies loaded successfully.")
        return True
    except Exception as e:
        logger.error(f"⚠️ Error loading cookies: {e}")
    return False

def get_stocktwits_url(ticker):
    return f"https://stocktwits.com/symbol/{ticker}"

def clean_text(text):
    """
    Remove URLs, non-alphanumeric characters, and extra whitespace.
    """
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def analyze_sentiments_advanced(text):
    """
    Combine TextBlob + VADER for a more robust approach.
    Weighted final score => 0.4 * TextBlob + 0.6 * VADER
    """
    tb_score = TextBlob(text).sentiment.polarity
    vader = SentimentIntensityAnalyzer()
    vd_score = vader.polarity_scores(text)["compound"]

    final_score = 0.4 * tb_score + 0.6 * vd_score

    if final_score > 0.2:
        category = "Bullish"
    elif final_score < -0.2:
        category = "Bearish"
    else:
        category = "Neutral"

    return tb_score, vd_score, final_score, category

def is_spam(message, threshold=SPAM_THRESHOLD):
    """
    Fuzzy matching for spam. Resets daily to avoid indefinite memory usage.
    """
    global recent_messages, message_list, spam_reset_time

    if datetime.now() > spam_reset_time:
        logger.info("⏲ Spam detection reset after 24 hours.")
        recent_messages.clear()
        message_list.clear()
        spam_reset_time = datetime.now() + timedelta(hours=SPAM_RESET_HOURS)

    if len(message) < 5:
        return False

    for recent in message_list:
        similarity = SequenceMatcher(None, message, recent).ratio()
        if similarity > threshold:
            return True

    if message not in recent_messages:
        recent_messages.add(message)
        message_list.append(message)
    if len(message_list) > MAX_SPAM_MESSAGES:
        oldest = message_list.pop(0)
        recent_messages.remove(oldest)
    return False

def scroll_and_collect(driver):
    """
    Scroll multiple times to load older messages, then return final HTML.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(MAX_SCROLLS):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    logger.info("✅ Scrolling complete, extracting messages.")
    return driver.page_source

def extract_messages(html_content):
    """
    Parse HTML from Stocktwits, gather messages w/timestamps, filter spam duplicates.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")
    messages = []
    spam_count = 0

    for msg in soup.find_all("div", class_="RichTextMessage_body__4qUeP"):
        try:
            timestamp_elem = msg.find_previous("time")
            content = msg.get_text(strip=True)
            timestamp = timestamp_elem.get("datetime") if timestamp_elem else None
            if content and timestamp:
                if is_spam(content):
                    spam_count += 1
                    continue
                messages.append({"timestamp": timestamp, "content": content})
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract a message: {e}")

    logger.info(f"✅ Extracted {len(messages)} unique messages. Filtered {spam_count} spam messages.")
    return messages

def append_to_csv_by_ticker_and_sentiment(processed_data):
    """
    Save or append processed sentiments into CSV by ticker & sentiment.
    """
    if not processed_data:
        logger.warning("⚠️ No data to append to CSV.")
        return

    grouped_data = {}
    for row in processed_data:
        ticker = row["ticker"]
        sentiment = row["sentiment_category"]
        filename = f"{ticker}_{sentiment}_sentiment.csv"
        ticker_dir = BASE_DATA_DIR / ticker
        ticker_dir.mkdir(parents=True, exist_ok=True)
        file_path = ticker_dir / filename
        grouped_data.setdefault(str(file_path), []).append(row)

    for file_path_str, rows in grouped_data.items():
        file_path = Path(file_path_str)
        df = pd.DataFrame(rows)
        file_exists = file_path.exists()
        df.to_csv(file_path, mode="a", header=not file_exists, index=False)
        logger.info(f"✅ Appended {len(df)} rows to {file_path}.")

def bulk_save_sentiment(processed_data):
    """
    Insert processed data in bulk to the database.
    """
    if not processed_data:
        logger.warning("⚠️ No data to save to the database.")
        return
    try:
        insert_data = [
            (
                row["ticker"],
                row["timestamp"],
                row["text"],
                row["textblob_sentiment_tb"],     
                row["textblob_sentiment_vader"],  
                row["sentiment_category"]
            )
            for row in processed_data
        ]
        db.bulk_insert_sentiment(insert_data)
    except Exception as e:
        logger.error(f"⚠️ Database bulk insert failed: {e}")

def cleanup_old_files(ticker, days=7):
    """
    Deletes old CSVs for each ticker older than X days.
    """
    ticker_dir = BASE_DATA_DIR / ticker
    if not ticker_dir.exists():
        return
    cutoff_date = datetime.now() - timedelta(days=days)
    for file in ticker_dir.glob(f"{ticker}_sentiment_*.csv"):
        try:
            parts = file.stem.split("_")
            timestamp_str = "_".join(parts[-2:])
            file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            if file_time < cutoff_date:
                file.unlink()
                logger.info(f"🗑️ Deleted old sentiment file: {file}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to parse timestamp for cleanup on {file}: {e}")

def parse_timestamp(iso_string):
    """
    Convert '2025-02-27T08:36:59Z' => 'YYYY-MM-DD HH:MM:SS'.
    """
    if iso_string.endswith("Z"):
        iso_string = iso_string.replace("Z", "+00:00")
    dt = datetime.fromisoformat(iso_string)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def single_ticker_scrape(ticker):
    """
    Create ephemeral driver for a single ticker. If it fails, 
    no other ticker is affected because each has its own driver.
    """
    driver = None
    try:
        driver = get_ephemeral_driver()
        url = get_stocktwits_url(ticker)
        driver.get(url)
        time.sleep(5)

        if load_cookies(driver):
            driver.refresh()
            time.sleep(3)

        html_content = scroll_and_collect(driver)
        messages = extract_messages(html_content)
        if not messages:
            logger.warning(f"No messages extracted for {ticker}.")
            return f"❌ No messages extracted for {ticker}.", []

        # Perform advanced sentiment analysis
        processed_data = []
        bullish = bearish = neutral = 0
        tb_total = 0.0
        vd_total = 0.0

        for msg in messages:
            text_clean = clean_text(msg["content"])
            if is_spam(text_clean):
                continue
            tb_score, vd_score, final_score, category = analyze_sentiments_advanced(text_clean)
            if category == "Bullish":
                bullish += 1
            elif category == "Bearish":
                bearish += 1
            else:
                neutral += 1

            tb_total += tb_score
            vd_total += vd_score

            data_row = {
                "ticker": ticker,
                "platform": "Stocktwits",
                "text": text_clean,
                "timestamp": parse_timestamp(msg["timestamp"]),
                "textblob_sentiment_tb": tb_score,
                "textblob_sentiment_vader": vd_score,
                "sentiment_category": category
            }
            processed_data.append(data_row)

        bulk_save_sentiment(processed_data)
        append_to_csv_by_ticker_and_sentiment(processed_data)
        cleanup_old_files(ticker, days=7)

        total_msgs = len(processed_data)
        avg_tb = tb_total / total_msgs if total_msgs else 0
        avg_vd = vd_total / total_msgs if total_msgs else 0

        summary = (
            f"📊 **{ticker} Sentiment Summary**\n"
            f"- Total messages: {total_msgs}\n"
            f"- Bullish: {bullish} ({(bullish/total_msgs)*100:.1f}%)\n"
            f"- Bearish: {bearish} ({(bearish/total_msgs)*100:.1f}%)\n"
            f"- Neutral: {neutral} ({(neutral/total_msgs)*100:.1f}%)\n"
            f"- Avg. TextBlob Score: {avg_tb:.3f}\n"
            f"- Avg. VADER Score: {avg_vd:.3f}"
        )
        logger.info(f"✅ Saved {total_msgs} messages for {ticker}.")
        return summary, processed_data

    except WebDriverException as e:
        logger.error(f"⚠️ WebDriverException scraping {ticker}: {e}")
        return f"⚠️ Error scraping {ticker}: {e}", []
    except Exception as e:
        logger.error(f"⚠️ Unexpected error for {ticker}: {e}")
        return f"⚠️ Error during scraping for {ticker}: {e}", []
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

# -------------------------------------------------------------------------
# Async Multi-Ticker Scraper
def get_embed_color(summary):
    if "Bearish" in summary:
        return discord.Color.red()
    elif "Bullish" in summary:
        return discord.Color.green()
    return discord.Color.light_gray()

async def run_multi_ticker_scraper(tickers=["TSLA", "SPY", "QQQ"], interval_minutes=15, run_duration_hours=8):
    """
    Repeatedly runs ephemeral scrapes for each ticker, 
    building a summary embed each iteration.
    """
    end_time = datetime.now() + timedelta(hours=run_duration_hours)
    logger.info(f"🚀 Starting overnight scraper until {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

    db_handler = DatabaseHandler(logger)

    while datetime.now() < end_time:
        ticker_summaries = []
        all_sentiments = []

        # Each ticker has its own ephemeral driver
        for ticker in tickers:
            summary, processed_data = await asyncio.to_thread(single_ticker_scrape, ticker)
            ticker_summaries.append(summary)
            all_sentiments.extend(processed_data)

        if all_sentiments:
            total_msgs = len(all_sentiments)
            bullish = sum(1 for d in all_sentiments if d["sentiment_category"] == "Bullish")
            bearish = sum(1 for d in all_sentiments if d["sentiment_category"] == "Bearish")
            neutral = sum(1 for d in all_sentiments if d["sentiment_category"] == "Neutral")

            market_sentiment = "Bullish" if bullish > bearish else "Bearish" if bearish > bullish else "Neutral"
            market_summary = (
                f"📊 **Market Sentiment Summary**\n"
                f"- Bullish: {bullish} ({(bullish/total_msgs)*100:.1f}%)\n"
                f"- Bearish: {bearish} ({(bearish/total_msgs)*100:.1f}%)\n"
                f"- Neutral: {neutral} ({(neutral/total_msgs)*100:.1f}%)\n"
                f"➡️ **Overall Market Sentiment:** {market_sentiment}"
            )
        else:
            market_summary = "No market sentiment data available."

        embed = discord.Embed(
            title="🕵️‍♂️ Overnight Sentiment Summary",
            color=(
                discord.Color.green() if "Bullish" in market_summary
                else discord.Color.red() if "Bearish" in market_summary
                else discord.Color.light_gray()
            )
        )

        for summary_text in ticker_summaries:
            lines = summary_text.split("\n")
            field_name = lines[0]
            field_value = "\n".join(lines[1:]).strip()
            embed.add_field(name=field_name, value=field_value, inline=False)

        embed.add_field(name="Market Sentiment Summary", value=market_summary, inline=False)
        embed.set_footer(text="Sentiment data updated in real-time.")

        yield embed
        logger.info(f"⏳ Sleeping {interval_minutes} minute(s) before next iteration.")
        await asyncio.sleep(interval_minutes * 60)

    db_handler.close_connection()
    logger.info("✅ Overnight scraping complete.")
