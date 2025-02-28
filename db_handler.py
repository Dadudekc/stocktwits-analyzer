import mysql.connector
import logging
from config import config

class DatabaseHandler:
    """
    Handles database operations for storing sentiment data.
    Supports MySQL as the backend.
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.db_type = config.get_env("DB_TYPE", "mysql").lower()

        if self.db_type != "mysql":
            raise ValueError("❌ Unsupported database type. Only MySQL is supported.")

        self.logger.info(f"✅ Initializing DatabaseHandler for {self.db_type}")
        self.conn = self.get_connection()
        self.cursor = self.conn.cursor()
        self._initialize_table()

    def get_connection(self):
        """Establishes a new database connection."""
        try:
            conn = mysql.connector.connect(
                database=config.get_env("MYSQL_DB_NAME"),
                user=config.get_env("MYSQL_DB_USER"),
                password=config.get_env("MYSQL_DB_PASSWORD"),
                host=config.get_env("MYSQL_DB_HOST", "localhost"),
                port=config.get_env("MYSQL_DB_PORT", 3306, int)
            )
            self.logger.info("✅ Database connection established.")
            return conn
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to MySQL: {e}")
            raise

    def close_connection(self):
        """Closes the database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        self.logger.info("✅ Database connection closed.")

    def _initialize_table(self):
        """Ensures SentimentData table exists."""
        query = """
        CREATE TABLE IF NOT EXISTS SentimentData (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ticker VARCHAR(10),
            timestamp DATETIME,
            content TEXT,
            textblob_sentiment FLOAT,
            vader_sentiment FLOAT,
            sentiment_category VARCHAR(20)
        );
        """
        try:
            self.cursor.execute(query)
            self.conn.commit()
            self.logger.info("✅ SentimentData table initialized successfully.")
        except Exception as e:
            self.logger.error(f"❌ Error initializing SentimentData table: {e}")

    def bulk_insert_sentiment(self, data):
        """Inserts multiple sentiment records in a batch transaction."""
        query = """
        INSERT INTO SentimentData (ticker, timestamp, content, textblob_sentiment, vader_sentiment, sentiment_category)
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        try:
            self.cursor.executemany(query, data)
            self.conn.commit()
            self.logger.info(f"✅ Bulk insert successful. Inserted {len(data)} records.")
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"⚠️ Database bulk insert failed: {e}")

    def save_sentiment(self, ticker, timestamp, content, textblob_sentiment, vader_sentiment, sentiment_category):
        """
        Saves a single sentiment data point into the database.
        """
        query = """
        INSERT INTO SentimentData (ticker, timestamp, content, textblob_sentiment, vader_sentiment, sentiment_category)
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        try:
            self.cursor.execute(query, (ticker, timestamp, content, textblob_sentiment, vader_sentiment, sentiment_category))
            self.conn.commit()
            self.logger.info(f"✅ Saved sentiment data for {ticker}.")
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"⚠️ Error saving sentiment data: {e}")

    def fetch_sentiment(self, ticker, limit=10):
        """
        Fetches the most recent sentiment data for a given ticker.

        :param ticker: Stock ticker symbol.
        :param limit: Maximum number of records to retrieve.
        :return: List of dictionaries containing sentiment data.
        """
        query = """
        SELECT timestamp, content, textblob_sentiment, vader_sentiment, sentiment_category
        FROM SentimentData WHERE ticker = %s ORDER BY timestamp DESC LIMIT %s;
        """
        try:
            self.cursor.execute(query, (ticker, limit))
            rows = self.cursor.fetchall()
            sentiment_data = []
            for row in rows:
                sentiment_data.append({
                    "timestamp": row[0],
                    "content": row[1],
                    "textblob_sentiment": row[2],
                    "vader_sentiment": row[3],
                    "sentiment_category": row[4]
                })
            return sentiment_data
        except Exception as e:
            self.logger.error(f"⚠️ Error fetching sentiment data: {e}")
            return []
