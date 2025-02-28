import os
import re
import requests
import subprocess
import logging
import json
import time
import unittest

import discord
from discord.ext import commands
from bs4 import BeautifulSoup
import openai
from dotenv import load_dotenv  # NEW: Load secrets from .env

# --------------------------------------------------------------------------
# Load Environment Variables from .env
# --------------------------------------------------------------------------
load_dotenv()  # This loads .env automatically
DISCORD_BOT_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHATGPT_SCRAPE_URL = os.getenv("CHATGPT_SCRAPE_URL", "https://chatgpt.com")

# Validate essentials
if not DISCORD_BOT_TOKEN:
    raise ValueError("DISCORD_TOKEN not found in .env or environment variables.")
if not DISCORD_CHANNEL_ID:
    raise ValueError("DISCORD_CHANNEL_ID not found in .env or environment variables.")

# Optional, but recommended for GPT usage
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    logging.warning("No OPENAI_API_KEY found. GPT-based fixes won't work unless you set this.")

# --------------------------------------------------------------------------
# Logging Setup
# --------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("AutoDevManager")

# --------------------------------------------------------------------------
# Directories & Constants
# --------------------------------------------------------------------------
SCRAPER_OUTPUT_DIR = "chatgpt_scraper_output"
os.makedirs(SCRAPER_OUTPUT_DIR, exist_ok=True)

# --------------------------------------------------------------------------
# ChatGPT Scraper
# --------------------------------------------------------------------------
class ChatGPTScraper:
    """
    Scrapes ChatGPT-like HTML responses from a URL (placeholder).
    Extracts code blocks and stores them into local files.
    """
    def __init__(self, url):
        self.url = url
        self.response_text = None
        self.extracted_code = {}

    def fetch_response(self):
        """Fetches the ChatGPT-generated response from a given URL."""
        try:
            r = requests.get(self.url)
            if r.status_code == 200:
                self.response_text = r.text
                return True
            else:
                logger.error(f"Fetch failed with status {r.status_code}")
                return False
        except requests.RequestException as e:
            logger.error(f"Error fetching ChatGPT response: {e}")
            return False

    def extract_code_blocks(self):
        """
        Finds <code> blocks, guesses language with regex on triple backticks.
        Saves each block as a .py or .<lang> file.
        """
        if not self.response_text:
            logger.warning("No response text to parse.")
            return None

        soup = BeautifulSoup(self.response_text, "html.parser")
        code_blocks = soup.find_all("code")

        for i, block in enumerate(code_blocks):
            language = "python"
            match = re.search(r"```(\w+)", block.text)
            if match:
                language = match.group(1)

            code_content = block.text.strip("```").strip()
            file_name = f"{SCRAPER_OUTPUT_DIR}/code_block_{i}.{language}"
            with open(file_name, "w") as f:
                f.write(code_content)
            self.extracted_code[file_name] = code_content

        logger.info(f"Extracted {len(self.extracted_code)} code blocks.")
        return self.extracted_code

# --------------------------------------------------------------------------
# Code Tester
# --------------------------------------------------------------------------
class CodeTester:
    """
    Finds .py files in SCRAPER_OUTPUT_DIR and attempts to run them,
    capturing stdout/stderr for each test or script file.
    """
    def __init__(self, code_dir=SCRAPER_OUTPUT_DIR):
        self.code_dir = code_dir

    def run_python_tests(self):
        """
        Runs every .py file in the directory, capturing output.
        If the file is a test, we can see if it passes or fails.
        Returns a dict {filename: output or error}
        """
        results = {}
        for file_name in os.listdir(self.code_dir):
            if file_name.endswith(".py"):
                file_path = os.path.join(self.code_dir, file_name)
                try:
                    proc = subprocess.run(
                        ["python", file_path],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if proc.returncode == 0:
                        results[file_name] = proc.stdout
                    else:
                        results[file_name] = proc.stderr
                except Exception as e:
                    results[file_name] = str(e)
        return results

# --------------------------------------------------------------------------
# AI Debugger (Self-Learning Loops)
# --------------------------------------------------------------------------
class AIDebugger:
    """
    Uses GPT to fix broken code iteratively.
    Tracks failures and resubmits code for refactoring until tests pass
    or max tries is reached.
    """
    def __init__(self, code_dir=SCRAPER_OUTPUT_DIR):
        self.code_dir = code_dir

    def call_gpt_debugger(self, error_message, code_content):
        if not OPENAI_API_KEY:
            logger.warning("No OPENAI_API_KEY; skipping AI debugging.")
            return code_content  # Return original code if no key

        prompt = f"""
        You are an AI debugging assistant. The Python code below has an error:

        <<CODE>>
        {code_content}

        <<ERROR>>
        {error_message}

        Provide ONLY the corrected code.
        """
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "system", "content": prompt}],
                temperature=0
            )
            return resp["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenAI Debugging call failed: {e}")
            return None

    def fix_code(self, file_path, error_msg):
        """
        Reads code from file, calls GPT for a fix, overwrites the file with the new code.
        """
        try:
            with open(file_path, "r") as f:
                original_code = f.read()

            fixed_code = self.call_gpt_debugger(error_msg, original_code)
            if not fixed_code:
                return False

            with open(file_path, "w") as f:
                f.write(fixed_code)
            return True
        except Exception as e:
            logger.error(f"Failed to fix code {file_path}: {e}")
            return False

    def self_learn_loop(self, tester, max_iter=5):
        """
        Runs tests, collects failures, calls fix_code, and retries until all pass or iterations exceed.
        Returns True if eventually successful, False otherwise.
        """
        for _ in range(max_iter):
            results = tester.run_python_tests()
            failed = {k: v for k, v in results.items() if "Traceback" in v}
            if not failed:
                return True  # All passed
            for file_name, error in failed.items():
                file_path = os.path.join(self.code_dir, file_name)
                success = self.fix_code(file_path, error)
                if not success:
                    return False
        return False

# --------------------------------------------------------------------------
# Discord Bot Implementation
# --------------------------------------------------------------------------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f"Bot connected as {bot.user}")
    channel = bot.get_channel(int(DISCORD_CHANNEL_ID))
    if channel:
        await channel.send("✅ AI Auto-Dev Manager is online! Use `!scrape` or `!test` commands to proceed.")

@bot.command(name="scrape")
async def scrape_command(ctx):
    """Command to attempt scraping a ChatGPT-like HTML and extracting code."""
    await ctx.send("🕵️ Scraping code blocks from ChatGPT response...")

    scraper = ChatGPTScraper(CHATGPT_SCRAPE_URL)
    success = scraper.fetch_response()
    if not success:
        await ctx.send("⚠️ Failed to fetch ChatGPT response. Check logs.")
        return

    extracted = scraper.extract_code_blocks()
    if not extracted:
        await ctx.send("No code blocks extracted.")
    else:
        await ctx.send(f"✅ Extracted {len(extracted)} code blocks into `{SCRAPER_OUTPUT_DIR}`")

@bot.command(name="test")
async def test_command(ctx):
    """Command to run all tests and attempt auto-fixes if tests fail."""
    await ctx.send("🔎 Running tests on extracted code...")

    tester = CodeTester()
    results = tester.run_python_tests()

    # Identify failures
    failed = {k: v for k, v in results.items() if "Traceback" in v}
    if not failed:
        await ctx.send("✅ All tests passed successfully!")
        return

    # Show failures
    fail_text = "\n".join([f"{k}:\n{v}" for k, v in failed.items()])
    await ctx.send(f"⚠️ Some tests failed:\n```{fail_text}```\nAttempting AI-based fixes now...")

    # Attempt AI debugging
    debugger = AIDebugger()
    success = debugger.self_learn_loop(tester, max_iter=5)
    if success:
        await ctx.send("✅ AI debugging succeeded! All tests now pass.")
    else:
        await ctx.send("❌ AI debugging could not fix all issues. Check logs for details.")

# --------------------------------------------------------------------------
# Main Entry: Launch the Discord Bot
# --------------------------------------------------------------------------
def main():
    logger.info("Starting the Discord Bot for AI Automated Dev Manager...")
    bot.run(DISCORD_BOT_TOKEN)

if __name__ == "__main__":
    main()
The "invalid session id" error suggests that Selenium's session is becoming stale or invalid between runs, even though we were creating ephemeral drivers per ticker. The issue may stem from:

Zombie sessions: Even though we quit the driver, it’s not properly being removed.
WebDriver mismatches: The WebDriver version might not be fully compatible with the latest Chrome update.
Driver crash before full execution: Selenium might be crashing unexpectedly before it properly closes.
🔥 New Fix: Double Validation Before Execution
We'll make sure that:

Session validation: Before running, check if the driver session is alive. If not, restart it.
Explicit cleanup: Ensure that the driver is force-quit after every execution, regardless of errors.
Graceful Recovery: If the session is invalid, it will restart automatically before retrying.
🚀 Updated Code with Session Validation & Recovery
python
Copy
Edit
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
from selenium.common.exceptions import WebDriverException, SessionNotCreatedException, NoSuchWindowException

# Sentiment Analysis
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Database Integration
from db_handler import DatabaseHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SentimentScraper")

BASE_DATA_DIR = Path(r"D:\SocialMediaManager\data")
BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)

db = DatabaseHandler(logger)

# -------------------- SESSION VALIDATION --------------------
def validate_driver(driver):
    """
    Ensures the WebDriver session is still alive before using it.
    Returns True if the driver is valid, otherwise False.
    """
    try:
        if driver is None:
            return False
        driver.execute_script("return document.readyState")  # Quick test
        return True
    except (WebDriverException, NoSuchWindowException):
        return False

def get_new_driver():
    """
    Creates a brand new Selenium driver session.
    """
    logger.info("🌐 Creating a new Selenium WebDriver session...")
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-extensions")
    options.add_argument("log-level=3")
    
    driver_path = ChromeDriverManager().install()
    return webdriver.Chrome(service=ChromeService(driver_path), options=options)

def restart_driver(driver):
    """
    Restarts a new driver if the session is invalid.
    """
    if driver:
        try:
            driver.quit()
        except Exception:
            pass
    return get_new_driver()

# -------------------- SCRAPING --------------------
def scroll_and_collect(driver):
    """
    Scrolls down the Stocktwits page to load all messages, then extracts HTML.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(10):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        las
