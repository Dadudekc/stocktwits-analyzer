import os
import sys
import importlib
import pytest
from unittest.mock import patch

# Ensure the parent directory is in sys.path so we can import config.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import logins.project_config as config_module

def reload_config():
    """Force reload the config module so that patched environment is picked up."""
    importlib.reload(config_module)
    return config_module

@pytest.fixture(autouse=True)
def disable_dotenv_and_clear_env(monkeypatch):
    """
    Disable loading of .env by patching find_dotenv and load_dotenv so they do nothing,
    and clear environment variables for required keys before each test.
    """
    monkeypatch.setattr("dotenv.find_dotenv", lambda: "")
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: None)
    for key in [
        "LINKEDIN_EMAIL", "LINKEDIN_PASSWORD", "TWITTER_EMAIL", "TWITTER_PASSWORD",
        "FACEBOOK_EMAIL", "FACEBOOK_PASSWORD", "INSTAGRAM_EMAIL", "INSTAGRAM_PASSWORD",
        "REDDIT_USERNAME", "REDDIT_PASSWORD", "DISCORD_TOKEN", "DISCORD_CHANNEL_ID",
        "ALPACA_API_KEY", "ALPACA_SECRET_KEY", "LOG_DIR"
    ]:
        monkeypatch.delenv(key, raising=False)
    yield

class TestConfig:
    # Define a complete set of environment variables for tests that require valid values.
    env_vars = {
        "DISCORD_CHANNEL_ID": "1234567890",
        "MAX_LOGIN_ATTEMPTS": "5",
        "LOGIN_WAIT_TIME": "8",
        "CAPTCHA_WAIT_TIME": "12",
        "DEBUG_MODE": "true",
        "ALPACA_API_KEY": "dummy_api_key",
        "ALPACA_SECRET_KEY": "dummy_secret_key",
        "LINKEDIN_EMAIL": "dummy_linkedin@example.com",
        "LINKEDIN_PASSWORD": "dummy",
        "TWITTER_EMAIL": "dummy_twitter@example.com",
        "TWITTER_PASSWORD": "dummy",
        "FACEBOOK_EMAIL": "dummy_facebook@example.com",
        "FACEBOOK_PASSWORD": "dummy",
        "INSTAGRAM_EMAIL": "dummy_instagram@example.com",
        "INSTAGRAM_PASSWORD": "dummy",
        "REDDIT_USERNAME": "dummy_reddit",
        "REDDIT_PASSWORD": "dummy",
        "DISCORD_TOKEN": "dummy_token",
        "LOG_DIR": "dummy_logs"
    }

    @pytest.fixture(autouse=True)
    def reload_config_fixture(self, monkeypatch):
        """
        Ensure that before each test the environment variables are cleared.
        This fixture runs automatically and lets individual tests set up their own environment.
        """
        for key in [
            "LINKEDIN_EMAIL", "LINKEDIN_PASSWORD", "TWITTER_EMAIL", "TWITTER_PASSWORD",
            "FACEBOOK_EMAIL", "FACEBOOK_PASSWORD", "INSTAGRAM_EMAIL", "INSTAGRAM_PASSWORD",
            "REDDIT_USERNAME", "REDDIT_PASSWORD", "DISCORD_TOKEN", "DISCORD_CHANNEL_ID",
            "ALPACA_API_KEY", "ALPACA_SECRET_KEY", "LOG_DIR"
        ]:
            monkeypatch.delenv(key, raising=False)
        yield

    def test_correct_type_casting(self):
        """Test that environment variables are correctly type-casted."""
        with patch.dict(os.environ, self.env_vars, clear=True):
            reload_config()  # Reload config after patching the environment
            config_inst = config_module.Config()
            assert hasattr(config_inst, "DISCORD_CHANNEL_ID"), "DISCORD_CHANNEL_ID attribute is missing"
            assert config_inst.DISCORD_CHANNEL_ID == 1234567890
            assert hasattr(config_inst, "MAX_LOGIN_ATTEMPTS"), "MAX_LOGIN_ATTEMPTS attribute is missing"
            assert config_inst.MAX_LOGIN_ATTEMPTS == 5

    def test_defaults_for_optional_variables(self):
        """Test that default values for optional environment variables are set."""
        # Provide required keys but do not set LOG_DIR.
        required_keys = {
            "LINKEDIN_EMAIL": "dummy_linkedin@example.com",
            "LINKEDIN_PASSWORD": "dummy",
            "TWITTER_EMAIL": "dummy_twitter@example.com",
            "TWITTER_PASSWORD": "dummy",
            "FACEBOOK_EMAIL": "dummy_facebook@example.com",
            "FACEBOOK_PASSWORD": "dummy",
            "INSTAGRAM_EMAIL": "dummy_instagram@example.com",
            "INSTAGRAM_PASSWORD": "dummy",
            "REDDIT_USERNAME": "dummy_reddit",
            "REDDIT_PASSWORD": "dummy",
            "DISCORD_TOKEN": "dummy_token",
            "DISCORD_CHANNEL_ID": "1234567890",
            "ALPACA_API_KEY": "dummy_api_key",
            "ALPACA_SECRET_KEY": "dummy_secret_key"
        }
        with patch.dict(os.environ, required_keys, clear=True):
            reload_config()
            config_inst = config_module.Config()
            expected_log_dir = os.path.join(os.getcwd(), "logs")
            assert config_inst.LOG_DIR == expected_log_dir

    def test_missing_env_variables(self):
        """
        Test that when required environment variables are present but empty,
        validate() raises a ValueError.
        """
        required_keys = [
            "LINKEDIN_EMAIL", "LINKEDIN_PASSWORD",
            "TWITTER_EMAIL", "TWITTER_PASSWORD",
            "FACEBOOK_EMAIL", "FACEBOOK_PASSWORD",
            "INSTAGRAM_EMAIL", "INSTAGRAM_PASSWORD",
            "REDDIT_USERNAME", "REDDIT_PASSWORD",
            "DISCORD_TOKEN", "DISCORD_CHANNEL_ID",
            "ALPACA_API_KEY", "ALPACA_SECRET_KEY"
        ]
        empty_vars = {key: "" for key in required_keys}
        with patch.dict(os.environ, empty_vars, clear=True):
            with pytest.raises(ValueError) as excinfo:
                # When we reload the config, instantiation of Config() should raise ValueError.
                reload_config()
            error_msg = str(excinfo.value)
            assert "Missing required config values" in error_msg
            for key in required_keys:
                assert key in error_msg

    def test_required_variables_set_correctly(self):
        """Ensure that required environment variables are correctly retrieved."""
        with patch.dict(os.environ, self.env_vars, clear=True):
            reload_config()
            config_inst = config_module.Config()
            assert hasattr(config_inst, "LINKEDIN_EMAIL"), "LINKEDIN_EMAIL attribute is missing"
            assert config_inst.LINKEDIN_EMAIL == self.env_vars["LINKEDIN_EMAIL"]

    def test_validation_error_message(self, monkeypatch):
        """
        Ensure that missing one required variable (e.g., TWITTER_EMAIL)
        produces the correct error message.
        """
        incomplete_vars = self.env_vars.copy()
        incomplete_vars.pop("TWITTER_EMAIL")
        for key, value in incomplete_vars.items():
            monkeypatch.setenv(key, value)
        monkeypatch.delenv("TWITTER_EMAIL", raising=False)
        assert os.getenv("TWITTER_EMAIL") is None
        with pytest.raises(ValueError) as excinfo:
            reload_config()
        error_msg = str(excinfo.value)
        assert "Missing required config values" in error_msg
        assert "TWITTER_EMAIL" in error_msg
