"""
D:\\SocialMediaManager\\platform_login_manager.py

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
from project_config import config  # ✅ Correct (using instance)
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

def is_logged_in(driver):
    """
    Checks if the user is logged into Instagram using multiple validation points:
    - Profile icon (Reliable but might change)
    - OneTap page (Might appear even if logged out)
    - Redirect Test: /direct/inbox/ (Strongest check)
    """
    try:
        # 🔹 Check for the profile icon (appears on most Instagram pages)
        driver.find_element(By.XPATH, "//div[contains(@aria-label, 'Profile')]")
        return True
    except:
        pass

    # 🔹 Check if redirected to the OneTap page
    if "accounts/onetap" in driver.current_url:
        return True

    # 🔹 Final Check: Navigate to Direct Messages & Check Redirection
    driver.get("https://www.instagram.com/direct/inbox/")
    time.sleep(5)
    
    if "login" in driver.current_url:
        logger.warning("🚨 Instagram login check failed: Redirected to login page.")
        return False

    logger.info("✅ Confirmed Instagram login via Direct Messages.")
    return True

def login_instagram(driver):
    platform = "instagram"
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(5)

    # Exit early if credentials are missing
    creds = SOCIAL_CREDENTIALS.get(platform, {})
    if not creds.get("email") or not creds.get("password"):
        logger.warning("⚠️ No Instagram credentials provided. Skipping login.")
        return  

    load_cookies(driver, platform)
    driver.refresh()
    time.sleep(5)

    # 🔹 Use enhanced login detection
    if is_logged_in(driver):
        logger.info("✅ Already logged into Instagram.")
        return

    try:
        username_field = driver.find_element(By.NAME, "username")
        password_field = driver.find_element(By.NAME, "password")
        username_field.send_keys(creds["email"])
        password_field.send_keys(creds["password"], Keys.RETURN)
        time.sleep(5)
    except Exception as e:
        logger.error("🚨 Automatic login error for Instagram: %s", e)

    # 🔹 Final check after login attempt
    if not is_logged_in(driver):
        logger.warning("⚠️ Instagram login failed. Manual login required.")
        wait_for_manual_login(driver, is_logged_in, platform)


    try:
        username_field = driver.find_element(By.NAME, "username")
        password_field = driver.find_element(By.NAME, "password")
        username_field.send_keys(creds["email"])
        password_field.send_keys(creds["password"], Keys.RETURN)
        time.sleep(5)
    except Exception as e:
        logger.error("🚨 Automatic login error for Instagram: %s", e)

    if not is_logged_in(driver):
        logger.warning("⚠️ Instagram login failed. Manual login required.")
        wait_for_manual_login(driver, is_logged_in, platform)

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
    Logs into Stocktwits with improved detection:
      - Loads cookies and refreshes
      - Attempts auto-login if necessary
      - Verifies login using Stocktwits Settings page
    """
    platform = "stocktwits"
    driver.get("https://stocktwits.com/signin")
    time.sleep(5)

    load_cookies(driver, platform)
    driver.refresh()
    time.sleep(5)

    # 🔹 Ultimate Login Check: If we can access Stocktwits settings, we are logged in
    def is_logged_in(d):
        d.get("https://stocktwits.com/settings/preferences")
        time.sleep(3)
        return "preferences" in d.current_url.lower()

    if is_logged_in(driver):
        logger.info("✅ Already logged into Stocktwits.")
        return

    creds = SOCIAL_CREDENTIALS.get(platform, {})
    if creds.get("email") and creds.get("password"):
        try:
            # 🔹 Locate login form elements dynamically
            username_field = driver.find_element(By.XPATH, "//input[@name='username' or contains(@id, 'email')]")
            password_field = driver.find_element(By.XPATH, "//input[@name='password' or contains(@id, 'password')]")
            login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Log In')]")

            username_field.send_keys(creds["email"])
            password_field.send_keys(creds["password"])
            login_button.click()  # Explicit click for reliability
            time.sleep(5)

        except Exception as e:
            logger.error("🚨 Automatic login error for %s: %s", platform, e)

    # 🔹 Final Verification: Navigate to settings page
    if not is_logged_in(driver):
        logger.warning("⚠️ Stocktwits login failed. Manual login required.")
        wait_for_manual_login(driver, is_logged_in, platform)

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
        login_stocktwits,
        login_twitter,
        login_facebook,
        login_instagram,
        login_reddit,
        login_linkedin  # Added Stocktwits login
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
