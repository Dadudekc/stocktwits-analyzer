import os
import sys
import asyncio
import logging
from pathlib import Path
import json
import pandas as pd
from datetime import datetime
import discord

# Import project components
from sentiment_scraper import (
    get_ephemeral_driver,
    load_cookies,
    analyze_sentiments_advanced,
    is_spam,
    get_stocktwits_url
)
from sentiment_analysis_discord_bot import (
    load_discord_credentials,
    classify_sentiment,
    create_embed
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BetaVerification")

class BetaVerifier:
    def __init__(self):
        self.verification_results = []
        self.base_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        
    def log_result(self, component: str, status: bool, message: str):
        """Log verification result with timestamp."""
        result = {
            "component": component,
            "status": "✅" if status else "❌",
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.verification_results.append(result)
        logger.info(f"{result['status']} {component}: {message}")

    async def verify_environment(self):
        """Verify environment setup and dependencies."""
        try:
            # Check Python version
            python_version = sys.version.split()[0]
            self.log_result(
                "Python Version",
                float(python_version.split('.')[0]) >= 3,
                f"Running Python {python_version}"
            )

            # Check required directories
            required_dirs = ['data', 'logs', 'backups']
            for dir_name in required_dirs:
                dir_path = self.base_dir / dir_name
                dir_path.mkdir(exist_ok=True)
                self.log_result(
                    f"Directory: {dir_name}",
                    dir_path.exists(),
                    f"Directory {'created' if not dir_path.exists() else 'exists'}"
                )

            # Check environment variables
            try:
                token, channel_id = load_discord_credentials()
                self.log_result(
                    "Discord Credentials",
                    bool(token and channel_id),
                    "Discord credentials loaded successfully"
                )
            except Exception as e:
                self.log_result(
                    "Discord Credentials",
                    False,
                    f"Failed to load Discord credentials: {str(e)}"
                )

        except Exception as e:
            self.log_result(
                "Environment Setup",
                False,
                f"Environment verification failed: {str(e)}"
            )

    async def verify_scraper(self):
        """Verify Stocktwits scraper functionality."""
        try:
            # Test driver creation
            driver = get_ephemeral_driver()
            self.log_result(
                "Selenium Driver",
                bool(driver),
                "Selenium driver created successfully"
            )

            # Test cookie loading
            cookie_status = load_cookies(driver)
            self.log_result(
                "Cookie Loading",
                cookie_status,
                "Cookies loaded successfully" if cookie_status else "No cookies found"
            )

            # Test sentiment analysis
            test_text = "TSLA is going to the moon! 🚀"
            tb_score, vd_score, final_score, category = analyze_sentiments_advanced(test_text)
            self.log_result(
                "Sentiment Analysis",
                all(isinstance(x, (int, float, str)) for x in [tb_score, vd_score, final_score, category]),
                f"Sentiment analysis working: {category} ({final_score:.2f})"
            )

            # Cleanup
            driver.quit()
            self.log_result(
                "Driver Cleanup",
                True,
                "Selenium driver closed successfully"
            )

        except Exception as e:
            self.log_result(
                "Scraper Verification",
                False,
                f"Scraper verification failed: {str(e)}"
            )

    async def verify_discord_bot(self):
        """Verify Discord bot functionality."""
        try:
            # Test sentiment classification
            test_text = "Market is looking bearish today"
            sentiment, score = classify_sentiment(test_text)
            self.log_result(
                "FinBERT Classification",
                bool(sentiment and score),
                f"Classification working: {sentiment} ({score:.2f})"
            )

            # Test embed creation
            test_embed = create_embed(
                "Test message with sentiment analysis results",
                discord.Color.blue()
            )
            self.log_result(
                "Discord Embed",
                bool(test_embed),
                "Embed creation working"
            )

        except Exception as e:
            self.log_result(
                "Discord Bot",
                False,
                f"Discord bot verification failed: {str(e)}"
            )

    def save_verification_report(self):
        """Save verification results to a JSON file."""
        report_path = self.base_dir / 'logs' / 'beta_verification.json'
        with open(report_path, 'w') as f:
            json.dump(self.verification_results, f, indent=2)
        logger.info(f"Verification report saved to {report_path}")

    def print_summary(self):
        """Print verification summary."""
        total = len(self.verification_results)
        passed = sum(1 for r in self.verification_results if r['status'] == '✅')
        failed = total - passed

        print("\n=== Beta Verification Summary ===")
        print(f"Total Checks: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print("==============================\n")

        if failed > 0:
            print("Failed Components:")
            for result in self.verification_results:
                if result['status'] == '❌':
                    print(f"- {result['component']}: {result['message']}")

async def main():
    verifier = BetaVerifier()
    
    # Run verifications
    await verifier.verify_environment()
    await verifier.verify_scraper()
    await verifier.verify_discord_bot()
    
    # Save and print results
    verifier.save_verification_report()
    verifier.print_summary()

if __name__ == "__main__":
    asyncio.run(main()) 