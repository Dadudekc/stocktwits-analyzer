"""
D:\SocialMediaManager\platform_login_manager.py

Handles the login process for multiple social media platforms using Selenium.
Leverages a persistent Chrome profile, stored cookies, and manual fallback
(for captchas or special login flows).

Supported Platforms:
  - LinkedIn
  - Twitter (X)
  - Facebook
  - Instagram
  - Reddit
  - Stocktwits
"""

import os
import time
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

# Load environment variables if needed (credentials, etc.)
load_dotenv()

# Import centralized config and logging
from config import config
from setup_logging import setup_logging

logger = setup_logging("platform_login", log_dir=os.path.join(os.getcwd(), "logs", "social"))

# Retrieve social credentials from your config; adapted to include Stocktwits.
SOCIAL_CREDENTIALS = {
    "linkedin": {
        "email": config.get_env("LINKEDIN_EMAIL"),
        "password": config.get_env("LINKEDIN_PASSWORD")
    },
    "twitter": {
        "email": config.get_env("TWITTER_EMAIL"),
        "password": config.get_env("TWITTER_PASSWORD")
    },
    "facebook": {
        "email": config.get_env("FACEBOOK_EMAIL"),
        "password": config.get_env("FACEBOOK_PASSWORD")
    },
    "instagram": {
        "email": config.get_env("INSTAGRAM_EMAIL"),
        "password": config.get_env("INSTAGRAM_PASSWORD")
    },
    "reddit": {
        "email": config.get_env("REDDIT_USERNAME"),
        "password": config.get_env("REDDIT_PASSWORD")
    },
    "stocktwits": {
        "email": config.get_env("STOCKTWITS_USERNAME"),
        "password": config.get_env("STOCKTWITS_PASSWORD")
    }
}

MAX_ATTEMPTS = 3  # Maximum manual login attempts

def get_driver(profile_path: str = None):
    """
    Returns a Selenium Chrome driver instance that uses a persistent profile.
    If profile_path is not provided, defaults to a folder named 'chrome_profile'
    in the current working directory (or as configured).
    """
    options = Options()
    options.add_argument("--start-maximized")
    
    if profile_path is None:
        profile_path = config.get_env("CHROME_PROFILE_PATH", os.path.join(os.getcwd(), "chrome_profile"))
    options.add_argument(f"--user-data-dir={profile_path}")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    logger.info("Chrome driver initialized with profile: %s", profile_path)
    return driver

def load_cookies(driver, platform):
    """
    Loads saved cookies for the given platform into the driver.
    """
    cookie_path = os.path.join("cookies", f"{platform}.pkl")
    if os.path.exists(cookie_path):
        with open(cookie_path, "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                cookie.pop("sameSite", None)
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    logger.error("Error adding cookie for %s: %s", platform, e)
        logger.info("Loaded cookies for %s", platform)
    else:
        logger.info("No cookies found for %s.", platform)

def save_cookies(driver, platform):
    """
    Saves the current session cookies for the given platform.
    """
    os.makedirs("cookies", exist_ok=True)
    cookie_path = os.path.join("cookies", f"{platform}.pkl")
    with open(cookie_path, "wb") as file:
        pickle.dump(driver.get_cookies(), file)
    logger.info("Saved cookies for %s", platform)

def wait_for_manual_login(driver, check_func, platform):
    """
    Allows manual login by prompting the user until a check function returns True
    (or until MAX_ATTEMPTS is reached).
    """
    attempts = 0
    while attempts < MAX_ATTEMPTS:
        input(f"Please complete the login for {platform} in the browser, then press Enter when done...")
        if check_func(driver):
            logger.info("%s login detected.", platform.capitalize())
            save_cookies(driver, platform)
            return True
        else:
            logger.warning("%s login not detected. Try again.", platform.capitalize())
            attempts += 1
    logger.error("Maximum attempts reached for %s.", platform)
    return False

# --------------------------------------------------------------------------
# Platform-Specific Login Methods
# --------------------------------------------------------------------------

def login_linkedin(driver):
    platform = "linkedin"
    driver.get("https://www.linkedin.com/login")
    time.sleep(3)
    
    load_cookies(driver, platform)
    driver.refresh()
    time.sleep(3)

    if "feed" in driver.current_url:
        logger.info("Already logged into LinkedIn.")
        return

    creds = SOCIAL_CREDENTIALS.get(platform, {})
    if creds.get("email") and creds.get("password"):
        try:
            driver.find_element(By.ID, "username").send_keys(creds["email"])
            driver.find_element(By.ID, "password").send_keys(creds["password"], Keys.RETURN)
        except Exception as e:
            logger.error("Automatic login error for %s: %s", platform, e)

    wait_for_manual_login(driver, lambda d: "feed" in d.current_url, platform)

def login_twitter(driver):
    platform = "twitter"
    driver.get("https://twitter.com/login")
    time.sleep(5)

    load_cookies(driver, platform)
    driver.refresh()
    time.sleep(5)

    if "home" in driver.current_url:
        logger.info("Already logged into Twitter.")
        return

    creds = SOCIAL_CREDENTIALS.get(platform, {})
    if creds.get("email") and creds.get("password"):
        try:
            email_field = driver.find_element(By.NAME, "text")
            email_field.send_keys(creds["email"], Keys.RETURN)
            time.sleep(3)
            try:
                driver.find_element(By.XPATH, "//span[contains(text(),'Next')]").click()
                time.sleep(3)
            except Exception:
                pass
            password_field = driver.find_element(By.NAME, "password")
            password_field.send_keys(creds["password"], Keys.RETURN)
        except Exception as e:
            logger.error("Automatic login error for %s: %s", platform, e)

    wait_for_manual_login(driver, lambda d: "home" in d.current_url, platform)

def login_facebook(driver):
    platform = "facebook"
    driver.get("https://www.facebook.com/login/")
    time.sleep(3)

    load_cookies(driver, platform)
    driver.refresh()
    time.sleep(3)

    def fb_logged_in(d):
        try:
            d.find_element(By.XPATH, "//div[contains(@aria-label, 'Create a post')]")
            return True
        except:
            return False

    if fb_logged_in(driver):
        logger.info("Already logged into Facebook.")
        return

    creds = SOCIAL_CREDENTIALS.get(platform, {})
    if creds.get("email") and creds.get("password"):
        try:
            driver.find_element(By.ID, "email").send_keys(creds["email"])
            driver.find_element(By.ID, "pass").send_keys(creds["password"], Keys.RETURN)
        except Exception as e:
            logger.error("Automatic login error for %s: %s", platform, e)

    wait_for_manual_login(driver, fb_logged_in, platform)

def login_instagram(driver):
    platform = "instagram"
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(5)

    load_cookies(driver, platform)
    driver.refresh()
    time.sleep(5)

    if "accounts/onetap" in driver.current_url or "instagram.com" in driver.current_url:
        logger.info("Already logged into Instagram.")
        return

    creds = SOCIAL_CREDENTIALS.get(platform, {})
    if creds.get("email") and creds.get("password"):
        try:
            driver.find_element(By.NAME, "username").send_keys(creds["email"])
            driver.find_element(By.NAME, "password").send_keys(creds["password"], Keys.RETURN)
        except Exception as e:
            logger.error("Automatic login error for %s: %s", platform, e)

    wait_for_manual_login(driver, lambda d: "instagram.com" in d.current_url, platform)

def login_reddit(driver):
    platform = "reddit"
    driver.get("https://www.reddit.com/login/")
    time.sleep(5)

    load_cookies(driver, platform)
    driver.refresh()
    time.sleep(5)

    if "reddit.com" in driver.current_url and "login" not in driver.current_url:
        logger.info("Already logged into Reddit.")
        return

    creds = SOCIAL_CREDENTIALS.get(platform, {})
    if creds.get("email") and creds.get("password"):
        try:
            time.sleep(3)
            username_field = driver.find_element(By.ID, "loginUsername")
            password_field = driver.find_element(By.ID, "loginPassword")
            username_field.send_keys(creds["email"])
            password_field.send_keys(creds["password"], Keys.RETURN)
        except Exception as e:
            logger.error("Automatic login error for %s: %s", platform, e)

    wait_for_manual_login(
        driver, 
        lambda d: ("reddit.com" in d.current_url and "login" not in d.current_url),
        platform
    )

# ------------------
# NEW: Stocktwits Login
# ------------------

def login_stocktwits(driver):
    """
    Logs into Stocktwits using a similar workflow:
      - Navigate to the Stocktwits login page.
      - Attempt to load cookies.
      - Refresh the page.
      - If not already logged in, try automatic login if credentials exist,
        and finally fall back to manual login.
    """
    platform = "stocktwits"
    driver.get("https://stocktwits.com/login")
    time.sleep(5)

    load_cookies(driver, platform)
    driver.refresh()
    time.sleep(5)

    # Check if already logged in: Stocktwits typically redirects away from '/login'
    if "login" not in driver.current_url.lower():
        logger.info("Already logged into Stocktwits.")
        return

    creds = SOCIAL_CREDENTIALS.get(platform, {})
    if creds.get("email") and creds.get("password"):
        try:
            # These element selectors might need adjustment based on Stocktwits' current layout.
            username_field = driver.find_element(By.NAME, "username")
            password_field = driver.find_element(By.NAME, "password")
            username_field.send_keys(creds["email"])
            password_field.send_keys(creds["password"], Keys.RETURN)
        except Exception as e:
            logger.error("Automatic login error for %s: %s", platform, e)

    wait_for_manual_login(driver, lambda d: "login" not in d.current_url.lower(), platform)

# --------------------------------------------------------------------------
# Master Method: Run All Logins
# --------------------------------------------------------------------------

def run_all_logins():
    """
    Iterates through each platform's login sequence, retaining session data
    in a persistent Chrome profile. This is often run once per day or as needed.
    """
    driver = get_driver()
    
    login_functions = [
        login_linkedin,
        login_twitter,
        login_facebook,
        login_instagram,
        login_reddit,
        login_stocktwits  # Added Stocktwits login
    ]
    
    for login_fn in login_functions:
        try:
            login_fn(driver)
        except Exception as e:
            logger.error("Error during %s: %s", login_fn.__name__, e)
    
    logger.info("All logins attempted. You may now close the browser or proceed with scraping.")
    driver.quit()

if __name__ == "__main__":
    run_all_logins()
