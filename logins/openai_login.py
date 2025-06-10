import os
import time
import json
import pickle
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import undetected_chromedriver as uc

# Use your existing setup_logging system
from setup_logging import setup_logging

logger = setup_logging("openai_login", log_dir=os.path.join(os.getcwd(), "logs", "social"))

# --- CONFIG ---
CHATGPT_URL = "https://chat.openai.com/"
COOKIE_FILE = os.path.join("cookies", "openai.pkl")

def get_openai_driver(profile_path=None, headless=False):
    """
    Returns a stealth Chrome driver using undetected_chromedriver.
    """
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")

    # Optional persistent Chrome profile
    if profile_path:
        options.add_argument(f"--user-data-dir={profile_path}")

    if headless:
        options.add_argument("--headless=new")

    driver = uc.Chrome(options=options)
    logger.info("✅ Undetected Chrome driver initialized for OpenAI.")
    return driver

def save_openai_cookies(driver):
    """
    Save OpenAI cookies to a pickle file.
    """
    os.makedirs("cookies", exist_ok=True)
    with open(COOKIE_FILE, "wb") as f:
        pickle.dump(driver.get_cookies(), f)
    logger.info("✅ Saved OpenAI cookies to %s", COOKIE_FILE)

def load_openai_cookies(driver):
    """
    Load OpenAI cookies from file and refresh the session.
    """
    if not os.path.exists(COOKIE_FILE):
        logger.warning("⚠️ No OpenAI cookie file found. Manual login may be required.")
        return False

    driver.get(CHATGPT_URL)
    time.sleep(2)

    with open(COOKIE_FILE, "rb") as f:
        cookies = pickle.load(f)

    for cookie in cookies:
        cookie.pop("sameSite", None)
        try:
            driver.add_cookie(cookie)
        except Exception as e:
            logger.error("❌ Error adding OpenAI cookie: %s", e)

    driver.refresh()
    time.sleep(5)
    logger.info("✅ OpenAI cookies loaded and page refreshed.")
    return True

def is_logged_in(driver):
    """
    Check if we are logged in to OpenAI ChatGPT.
    """
    driver.get(CHATGPT_URL)
    time.sleep(3)

    try:
        driver.find_element(By.TAG_NAME, "textarea")
        logger.info("✅ OpenAI login detected (textarea found).")
        return True
    except Exception:
        logger.warning("⚠️ OpenAI login not detected (textarea missing).")
        return False

def login_openai(driver):
    """
    Login handler for OpenAI/ChatGPT using cookies or manual fallback.
    """
    logger.info("🔐 Starting OpenAI login process...")

    # Step 1: Load cookies if they exist
    if load_openai_cookies(driver) and is_logged_in(driver):
        logger.info("✅ OpenAI auto-login successful with cookies.")
        return True

    # Step 2: Manual login
    logger.warning("⚠️ Manual login required. Navigating to login page...")
    driver.get("https://chat.openai.com/auth/login")
    time.sleep(5)

    input("👉 Please manually complete the login + verification and press ENTER here...")

    if is_logged_in(driver):
        save_openai_cookies(driver)
        logger.info("✅ Manual OpenAI login successful. Cookies saved.")
        return True
    else:
        logger.error("❌ Manual OpenAI login failed. Try again.")
        return False

# --------------------
# Test Run (Optional)
# --------------------
if __name__ == "__main__":
    # Optional standalone test run
    driver = get_openai_driver(profile_path="chrome_profile/openai", headless=False)
    
    if login_openai(driver):
        logger.info("🎉 OpenAI Login Complete!")
    else:
        logger.error("❌ OpenAI Login Failed.")

    time.sleep(10)
    driver.quit()
