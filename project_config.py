import os
import logging
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
from setup_logging import setup_logging

# Setup logging using your custom setup_logging function.
logger = setup_logging("config", log_dir=os.path.join(os.getcwd(), "logs", "social"))

# Load environment variables from .env if available.
ENV_PATH = find_dotenv()
if ENV_PATH:
    load_dotenv(ENV_PATH)
    logger.info(f"✅ Loaded environment variables from: {ENV_PATH}")
else:
    logger.warning("⚠️ WARNING: No .env file found! Ensure your environment variables are set manually.")


class Config:
    """Centralized configuration handler for SocialMediaManager."""

    def __init__(self):
        """Initialize and load environment variables into instance properties."""
        self.load_env()      # Load all environment variables.
        self.validate()      # Automatically check for missing values on startup.

    def load_env(self):
        """Load environment variables into instance properties."""
        # Required Login Credentials
        self.LINKEDIN_EMAIL = self.get_env("LINKEDIN_EMAIL")
        self.LINKEDIN_PASSWORD = self.get_env("LINKEDIN_PASSWORD")
        self.TWITTER_EMAIL = self.get_env("TWITTER_EMAIL")
        self.TWITTER_PASSWORD = self.get_env("TWITTER_PASSWORD")
        self.FACEBOOK_EMAIL = self.get_env("FACEBOOK_EMAIL")
        self.FACEBOOK_PASSWORD = self.get_env("FACEBOOK_PASSWORD")
        self.INSTAGRAM_EMAIL = self.get_env("INSTAGRAM_EMAIL")
        self.INSTAGRAM_PASSWORD = self.get_env("INSTAGRAM_PASSWORD")
        self.REDDIT_USERNAME = self.get_env("REDDIT_USERNAME")
        self.REDDIT_PASSWORD = self.get_env("REDDIT_PASSWORD")

        # API Keys & Tokens
        self.DISCORD_TOKEN = self.get_env("DISCORD_TOKEN")
        self.DISCORD_CHANNEL_ID = self.get_env("DISCORD_CHANNEL_ID", default=0, cast_type=int)
        self.ALPACA_API_KEY = self.get_env("ALPACA_API_KEY")
        self.ALPACA_SECRET_KEY = self.get_env("ALPACA_SECRET_KEY")

        # Logging & Directories
        self.LOG_DIR = self.get_env("LOG_DIR", os.path.join(os.getcwd(), "logs"))
        self.LOG_LEVEL = self.get_env("LOG_LEVEL", "INFO")

        # Browser & Session Configurations
        self.CHROME_PROFILE_PATH = self.get_env("CHROME_PROFILE_PATH", os.path.join(os.getcwd(), "chrome_profile"))
        self.COOKIE_STORAGE_PATH = self.get_env("COOKIE_STORAGE_PATH", os.path.join(os.getcwd(), "cookies"))

        # Security & Session Settings
        self.MAX_LOGIN_ATTEMPTS = self.get_env("MAX_LOGIN_ATTEMPTS", 3, cast_type=int)
        self.LOGIN_WAIT_TIME = self.get_env("LOGIN_WAIT_TIME", 5, cast_type=int)
        self.CAPTCHA_WAIT_TIME = self.get_env("CAPTCHA_WAIT_TIME", 10, cast_type=int)
        self.DEBUG_MODE = self.get_env("DEBUG_MODE", "false").lower() == "true"

    def get_env(self, key: str, default=None, cast_type=None):
        """
        Retrieve an environment variable with optional type conversion.
        If the variable is missing or empty, it falls back to the default value.
        """
        value = os.getenv(key, default)
        
        # 🔹 Ensure `None` never gets passed to `.lower()` or similar
        if value is None:
            return default

        if cast_type:
            try:
                return cast_type(value)
            except ValueError:
                logger.warning(f"⚠️ Failed to cast {key} to {cast_type.__name__}. Using default: {default}")
                return default

        return value


    def validate(self):
        """Ensures all required credentials and settings are set."""
        required_keys = [
            "LINKEDIN_EMAIL", "LINKEDIN_PASSWORD",
            "TWITTER_EMAIL", "TWITTER_PASSWORD",
            "FACEBOOK_EMAIL", "FACEBOOK_PASSWORD",
            "INSTAGRAM_EMAIL", "INSTAGRAM_PASSWORD",
            "REDDIT_USERNAME", "REDDIT_PASSWORD",
            "DISCORD_TOKEN", "DISCORD_CHANNEL_ID",
            "ALPACA_API_KEY", "ALPACA_SECRET_KEY"
        ]
        missing_keys = []
        for key in required_keys:
            value = getattr(self, key, None)
            if value is None:
                missing_keys.append(key)
            elif isinstance(value, str) and not value.strip():
                missing_keys.append(key)
            elif isinstance(value, int) and value == 0:
                missing_keys.append(key)
        if missing_keys:
            error_msg = f"🚨 Missing required config values: {', '.join(missing_keys)}"
            logger.error(error_msg)
            raise ValueError(error_msg)


# 🔹 **Ensure config is always available when imported**
config = Config()  # ✅ Fix: Now other files can import `config` as an instance.

