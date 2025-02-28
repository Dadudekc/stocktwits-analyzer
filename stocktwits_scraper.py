"""
File: stocktwits_scraper.py
Description:
------------
Scrapes Stocktwits trending discussions & sentiment using Selenium.
Handles authentication, scrolling, and text sentiment analysis.
"""

import os
import time
import json
import sqlite3
import pandas as pd
import re
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from bs4 import BeautifulSoup

# --------------------------------------------------------------------------
# Logging Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Constants
STOCKTWITS_URL = "https://stocktwits.com/symbol/TSLA"
COOKIE_FILE = "stocktwits_cookies.json"
DB_FILE = "stocktwits_sentiment.db"
MAX_SCROLLS = 10
SCROLL_PAUSE = 2

# --------------------------------------------------------------------------
# Setup Database
def setup_database():
    """Creates or initializes the database for storing sentiment data."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS SentimentData (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            timestamp TEXT,
            content TEXT,
            textblob_sentiment REAL,
            vader_sentiment REAL,
            UNIQUE(ticker, timestamp, content)
        )
        """
    )
    conn.commit()
    conn.close()
    logger.info("✅ Database initialized.")

setup_database()

# --------------------------------------------------------------------------
# Selenium Setup
def get_driver():
    """Initializes Selenium Chrome Driver with proper options."""
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-extensions")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("log-level=3")

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# --------------------------------------------------------------------------
# Cookie Handling
def load_cookies(driver):
    """Loads Stocktwits cookies if available."""
    if os.path.exists(COOKIE_FILE):
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

def save_cookies(driver):
    """Saves cookies after successful login."""
    try:
        cookies = driver.get_cookies()
        with open(COOKIE_FILE, "w") as f:
            json.dump(cookies, f, indent=4)
        logger.info("✅ Cookies saved successfully.")
    except Exception as e:
        logger.error(f"⚠️ Error saving cookies: {e}")

# --------------------------------------------------------------------------
# Check if Logged In
def is_logged_in(driver):
    """Checks if the user is logged into Stocktwits."""
    return "stocktwits.com" in driver.current_url and "signin" not in driver.current_url

# --------------------------------------------------------------------------
# Scroll & Extract Data
def scroll_and_collect(driver):
    """Scrolls through Stocktwits and extracts stock discussion messages."""
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
    """Parses Stocktwits HTML and extracts messages & timestamps."""
    soup = BeautifulSoup(html_content, "html.parser")
    messages = []

    for msg in soup.find_all("div", class_="RichTextMessage_body__4qUeP"):
        try:
            timestamp_elem = msg.find_previous("time")
            content = msg.get_text(strip=True)
            timestamp = timestamp_elem.get("datetime") if timestamp_elem else None
            if content and timestamp:
                messages.append({"timestamp": timestamp, "content": content})
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract a message: {e}")

    logger.info(f"✅ Extracted {len(messages)} messages.")
    return pd.DataFrame(messages)

# --------------------------------------------------------------------------
# Text Cleaning & Sentiment Analysis
def clean_text(text):
    """Removes URLs, special characters, and unnecessary whitespace."""
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def analyze_sentiments(text):
    """Performs sentiment analysis using TextBlob & VADER."""
    textblob_score = TextBlob(text).sentiment.polarity
    vader_analyzer = SentimentIntensityAnalyzer()
    vader_score = vader_analyzer.polarity_scores(text)["compound"]
    return textblob_score, vader_score

def insert_sentiment_data(ticker, df):
    """Inserts sentiment analysis results into the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    for _, row in df.iterrows():
        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO SentimentData 
                (ticker, timestamp, content, textblob_sentiment, vader_sentiment)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    ticker,
                    row["timestamp"],
                    row["content"],
                    row["textblob_sentiment"],
                    row["vader_sentiment"],
                ),
            )
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    logger.info("✅ Sentiment data inserted into database.")

# --------------------------------------------------------------------------
# Main Scraper Logic
def scrape_stocktwits():
    """Main function: logs in, scrapes messages, analyzes sentiment, saves data."""
    driver = get_driver()
    driver.get(STOCKTWITS_URL)
    time.sleep(5)

    if load_cookies(driver):
        driver.refresh()
        time.sleep(3)

    if not is_logged_in(driver):
        input("🚀 Please log in manually and press Enter when done...")
        save_cookies(driver)

    html_content = scroll_and_collect(driver)
    driver.quit()

    messages_df = extract_messages(html_content)
    messages_df["clean_content"] = messages_df["content"].apply(clean_text)
    messages_df["textblob_sentiment"], messages_df["vader_sentiment"] = zip(*messages_df["clean_content"].map(analyze_sentiments))

    insert_sentiment_data("TSLA", messages_df)
    messages_df.to_csv("TSLA_sentiment.csv", index=False)
    logger.info("✅ Data saved to TSLA_sentiment.csv")

if __name__ == "__main__":
    scrape_stocktwits()
