"""
File: config.py
Path: D:\SocialMediaManager\config.py

Description:
------------
Handles centralized configuration for SocialMediaManager.
Reads environment variables dynamically (with .env support) to allow test overrides.
Exposes API credentials, login settings, and logging configurations as properties.
"""

import os
from dotenv import load_dotenv, find_dotenv

# Locate and load the .env file
ENV_PATH = find_dotenv()

if ENV_PATH:
    load_dotenv(ENV_PATH)
    print(f"✅ Loaded environment variables from: {ENV_PATH}")
else:
    print("⚠️ WARNING: No .env file found! Ensure your environment variables are set manually.")

class Config:
    """Centralized configuration handler for SocialMediaManager."""

    @staticmethod
    def get_env(key: str, default=None, cast_type=None):
        """Helper to retrieve environment variables with optional type conversion."""
        value = os.getenv(key, default)
        return cast_type(value) if cast_type and value is not None else value

    # Social Media Credentials
    @property
    def LINKEDIN_EMAIL(self):
        return self.get_env("LINKEDIN_EMAIL")

    @property
    def LINKEDIN_PASSWORD(self):
        return self.get_env("LINKEDIN_PASSWORD")

    @property
    def TWITTER_EMAIL(self):
        return self.get_env("TWITTER_EMAIL")

    @property
    def TWITTER_PASSWORD(self):
        return self.get_env("TWITTER_PASSWORD")

    @property
    def FACEBOOK_EMAIL(self):
        return self.get_env("FACEBOOK_EMAIL")

    @property
    def FACEBOOK_PASSWORD(self):
        return self.get_env("FACEBOOK_PASSWORD")

    @property
    def INSTAGRAM_EMAIL(self):
        return self.get_env("INSTAGRAM_EMAIL")

    @property
    def INSTAGRAM_PASSWORD(self):
        return self.get_env("INSTAGRAM_PASSWORD")

    @property
    def REDDIT_USERNAME(self):
        return self.get_env("REDDIT_USERNAME")

    @property
    def REDDIT_PASSWORD(self):
        return self.get_env("REDDIT_PASSWORD")

    # Discord Bot Credentials
    @property
    def DISCORD_BOT_TOKEN(self):
        return self.get_env("DISCORD_TOKEN")

    @property
    def DISCORD_CHANNEL_ID(self):
        return self.get_env("DISCORD_CHANNEL_ID", cast_type=int)

    # Logging Configuration
    @property
    def LOG_DIR(self):
        return self.get_env("LOG_DIR", os.path.join(os.getcwd(), "logs"))

    @property
    def LOG_LEVEL(self):
        return self.get_env("LOG_LEVEL", "INFO")

    # Web Scraping & Selenium Settings
    @property
    def CHROME_PROFILE_PATH(self):
        return self.get_env("CHROME_PROFILE_PATH", os.path.join(os.getcwd(), "chrome_profile"))

    @property
    def MAX_LOGIN_ATTEMPTS(self):
        return self.get_env("MAX_LOGIN_ATTEMPTS", 3, int)

    @property
    def LOGIN_WAIT_TIME(self):
        """Time (in seconds) to wait for manual login before retrying."""
        return self.get_env("LOGIN_WAIT_TIME", 5, int)

    @property
    def CAPTCHA_WAIT_TIME(self):
        """Time (in seconds) to wait for captcha resolution before retrying."""
        return self.get_env("CAPTCHA_WAIT_TIME", 10, int)

    # Cookie Management
    @property
    def COOKIE_STORAGE_PATH(self):
        return self.get_env("COOKIE_STORAGE_PATH", os.path.join(os.getcwd(), "cookies"))

    # Execution Mode
    @property
    def DEBUG_MODE(self):
        return self.get_env("DEBUG_MODE", "false").lower() == "true"

    # Validation
    def validate(self):
        """Ensure required credentials and settings are set."""
        required_keys = [
            "LINKEDIN_EMAIL", "LINKEDIN_PASSWORD",
            "TWITTER_EMAIL", "TWITTER_PASSWORD",
            "FACEBOOK_EMAIL", "FACEBOOK_PASSWORD",
            "INSTAGRAM_EMAIL", "INSTAGRAM_PASSWORD",
            "REDDIT_USERNAME", "REDDIT_PASSWORD",
            "DISCORD_BOT_TOKEN", "DISCORD_CHANNEL_ID"
        ]
        missing_keys = [key for key in required_keys if not getattr(self, key)]
        if missing_keys:
            raise ValueError(f"🚨 Missing required config values: {', '.join(missing_keys)}")


# Singleton instance for consistent configuration usage
config = Config()

# Validate configuration at runtime
try:
    config.validate()
except ValueError as e:
    print(f"⚠️ Configuration Error: {e}")
