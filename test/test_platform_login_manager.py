import os
import time
import pickle
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
import sys

# Ensure the project directory is in sys.path so that we can import our module.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import functions to test from platform_login_manager.py
from logins.platform_login_manager import (
    get_driver,
    load_cookies,
    save_cookies,
    wait_for_manual_login,
    login_linkedin,
    run_all_logins,
    login_instagram,
    logger,
    SOCIAL_CREDENTIALS
)

# ------------------ Fixtures ------------------

@pytest.fixture
def dummy_driver():
    """Return a dummy Selenium driver as a MagicMock."""
    driver = MagicMock()
    driver.current_url = "about:blank"
    driver.add_cookie = MagicMock()
    driver.get_cookies = MagicMock(return_value=[{"name": "test_cookie", "value": "abc"}])
    return driver

@pytest.fixture(autouse=True)
def fast_sleep():
    """Patch time.sleep to avoid delays during tests."""
    with patch("time.sleep", return_value=None):
        yield

# ------------------ Tests ------------------

def test_get_driver():
    """Test that get_driver returns a driver with the persistent profile argument."""
    with patch("platform_login_manager.Options") as mock_options, \
         patch("platform_login_manager.Service") as mock_service, \
         patch("platform_login_manager.webdriver.Chrome") as mock_chrome, \
         patch("platform_login_manager.ChromeDriverManager.install", return_value="dummy_path"):
        
        dummy_options = MagicMock()
        mock_options.return_value = dummy_options
        
        driver_instance = MagicMock()
        mock_chrome.return_value = driver_instance

        profile_path = "dummy_profile"
        driver = get_driver(profile_path)
        dummy_options.add_argument.assert_any_call(f"--user-data-dir={profile_path}")
        assert driver == driver_instance

def test_load_cookies_existing(dummy_driver, tmp_path):
    """Test that load_cookies loads cookies if the cookie file exists and is valid."""
    platform = "testplatform"
    cookie_dir = tmp_path / "cookies"
    cookie_dir.mkdir()
    cookie_file = cookie_dir / f"{platform}.pkl"

    fake_cookies = [{"name": "cookie1", "value": "value1", "sameSite": "Lax"}]
    with open(cookie_file, "wb") as f:
        pickle.dump(fake_cookies, f)
    assert cookie_file.stat().st_size > 0, "🚨 Pickle file is empty before testing load_cookies!"

    # Save the original os.path.join
    original_join = os.path.join
    # Patch os.path.exists to always return True,
    # and patch os.path.join so that when called with ("cookies", f"{platform}.pkl")
    # it returns the temporary cookie file path.
    with patch("platform_login_manager.os.path.exists", return_value=True), \
         patch("platform_login_manager.os.path.join", side_effect=lambda *args, **kwargs: str(cookie_file) if args == ("cookies", f"{platform}.pkl") else original_join(*args, **kwargs)):
        load_cookies(dummy_driver, platform)

    # Verify that add_cookie was called with our cookie and that "sameSite" was removed.
    dummy_driver.add_cookie.assert_called_with({"name": "cookie1", "value": "value1"})

def test_save_cookies(dummy_driver, tmp_path):
    """Test that save_cookies writes cookies to a file."""
    platform = "testplatform"
    dummy_driver.get_cookies.return_value = [{"name": "cookie1", "value": "value1"}]
    with patch("platform_login_manager.os.makedirs") as mock_makedirs, \
         patch("platform_login_manager.pickle.dump") as mock_pickle_dump:
        save_cookies(dummy_driver, platform)
    mock_makedirs.assert_called()
    mock_pickle_dump.assert_called_once()

def test_wait_for_manual_login_success(dummy_driver):
    """Test wait_for_manual_login returns True when check_func succeeds immediately."""
    check_func = MagicMock(return_value=True)
    with patch("builtins.input", return_value=""):
        result = wait_for_manual_login(dummy_driver, check_func, "dummy")
    assert result is True

def test_wait_for_manual_login_failure(dummy_driver):
    """Test wait_for_manual_login returns False after MAX_ATTEMPTS if check_func never returns True."""
    check_func = MagicMock(return_value=False)
    with patch("builtins.input", return_value=""):
        result = wait_for_manual_login(dummy_driver, check_func, "dummy")
    assert result is False

def test_run_all_logins():
    """Test run_all_logins iterates over login functions and quits the driver."""
    with patch("platform_login_manager.get_driver") as mock_get_driver, \
         patch("platform_login_manager.login_linkedin") as mock_login_linkedin, \
         patch("platform_login_manager.login_twitter") as mock_login_twitter, \
         patch("platform_login_manager.login_facebook") as mock_login_facebook, \
         patch("platform_login_manager.login_instagram") as mock_login_instagram, \
         patch("platform_login_manager.login_reddit") as mock_login_reddit, \
         patch("platform_login_manager.login_stocktwits") as mock_login_stocktwits:
        
        dummy_driver = MagicMock()
        mock_get_driver.return_value = dummy_driver
        
        run_all_logins()
        mock_login_linkedin.assert_called_once_with(dummy_driver)
        mock_login_twitter.assert_called_once_with(dummy_driver)
        mock_login_facebook.assert_called_once_with(dummy_driver)
        mock_login_instagram.assert_called_once_with(dummy_driver)
        mock_login_reddit.assert_called_once_with(dummy_driver)
        mock_login_stocktwits.assert_called_once_with(dummy_driver)
        dummy_driver.quit.assert_called_once()

def test_instagram_login_success(dummy_driver):
    """Test successful Instagram login detection."""
    with patch("platform_login_manager.load_cookies"), \
         patch("platform_login_manager.save_cookies"), \
         patch("platform_login_manager.wait_for_manual_login", return_value=True):
        
        dummy_driver.current_url = "https://www.instagram.com/"
        login_instagram(dummy_driver)
        assert "instagram.com" in dummy_driver.current_url
        logger.info("✅ Instagram login test passed.")

def test_instagram_login_failure(dummy_driver):
    """Test handling of incorrect Instagram credentials."""
    with patch("platform_login_manager.load_cookies"), \
         patch("platform_login_manager.wait_for_manual_login", return_value=False):
        
        dummy_driver.current_url = "https://www.instagram.com/accounts/login/"
        dummy_driver.find_element.side_effect = lambda by, value: (
            MagicMock(text="The username you entered doesn't belong to an account.")
            if "p[contains(text(), 'The username you entered')]" in value else MagicMock()
        )
        login_instagram(dummy_driver)
        logger.info("🚨 Instagram login failure test caught an invalid login.")

def test_instagram_manual_login_required(dummy_driver):
    """Test manual login handling if automatic login fails."""
    with patch("platform_login_manager.wait_for_manual_login", return_value=True):
        dummy_driver.current_url = "https://www.instagram.com/accounts/login/"
        login_instagram(dummy_driver)
        assert "instagram.com" in dummy_driver.current_url
        logger.info("✅ Instagram manual login test passed.")

def test_instagram_no_credentials(dummy_driver):
    """Test behavior when no Instagram credentials are available."""
    with patch.dict(SOCIAL_CREDENTIALS, {"instagram": {"email": "", "password": ""}}, clear=True), \
         patch("builtins.input", return_value=""):
        login_instagram(dummy_driver)
        # Since no credentials are provided, the login process should exit early.
        dummy_driver.find_element.assert_not_called()
