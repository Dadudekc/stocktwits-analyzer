import os
from pathlib import Path

class Config:
    def __init__(self):
        self.BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
        self.DATA_DIR = self.BASE_DIR / 'data'
        self.LOG_DIR = self.BASE_DIR / 'logs'
        self.BACKUP_DIR = self.BASE_DIR / 'backups'
        
        # Create required directories
        for directory in [self.DATA_DIR, self.LOG_DIR, self.BACKUP_DIR]:
            directory.mkdir(exist_ok=True)
        
        # Discord Configuration
        self.DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', 'your_discord_bot_token_here')
        self.DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', '0'))
        
        # Scraping Configuration
        self.SCRAPE_INTERVAL_MINUTES = int(os.getenv('SCRAPE_INTERVAL_MINUTES', '15'))
        self.TICKERS = os.getenv('TICKERS', 'TSLA,SPY,QQQ').split(',')
        
        # Database Configuration
        self.DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{self.DATA_DIR}/sentiment.db')
        
        # Logging Configuration
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        
    def get_env(self, key, default=None, cast_type=str):
        """Get environment variable with optional type casting."""
        value = os.getenv(key, default)
        if value is None:
            return None
        try:
            return cast_type(value)
        except (ValueError, TypeError):
            return default

# Create global config instance
config = Config() 