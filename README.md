# 🧠 **Sentiment Scraper**

A real-time, multi-ticker sentiment analysis engine for financial data. Supports Stocktwits scraping, spam filtering, sentiment scoring (TextBlob + VADER), and stores results in a local or remote database. Ideal for algorithmic trading, trend tracking, or social signal extraction.

---

## 📸 Demo

![Sentiment Analysis Dashboard](docs/images/dashboard_preview.png)
*Real-time sentiment analysis dashboard showing multi-ticker monitoring*

![Discord Integration](docs/images/discord_preview.png)
*Automated Discord updates with sentiment summaries*

---

## 🚀 Features

* **🧰 Dual Sentiment Engines**
  * TextBlob + VADER integrated for cross-verified sentiment scoring
  * Supports polarity, subjectivity, and compound score analysis

* **🧹 Spam Filtering**
  * Excludes posts/comments based on keyword noise, repetition, and source heuristics
  * Daily reset of spam detection to prevent memory bloat

* **📦 Multi-Ticker Support**
  * Scrape sentiment data across multiple stock symbols in parallel
  * Customizable scrape intervals via config
  * Default monitoring of TSLA, SPY, QQQ

* **🗃️ Database Integration**
  * Auto-inserts scraped data into SQLite
  * Deduplicates entries and enforces schema consistency
  * Automated data cleanup and archival

* **🧼 Automated File Cleanup**
  * Old logs, temp data, and duplicate records are pruned on cycle restart
  * Configurable retention periods

* **🔁 Scheduled + Manual Modes**
  * Supports scheduled runs with configurable intervals
  * Manual one-off triggers for specific tickers

* **📢 Social Media Integration**
  * ✅ Agent devlogs are automatically posted to Discord using undetected browser automation
  * Rich embed messages with sentiment summaries
  * Configurable update intervals

---

## 🗂️ Project Structure

```
sentiment_scraper/
├── data/                    # Data storage directory
├── models/                  # ML models and configurations
├── drivers/                 # Web driver configurations
├── logins/                  # Authentication and configuration
├── logs/                    # Application logs
├── test/                    # Test suite
├── backups/                 # Backup files
├── deployed/                # Deployment configurations
├── docs/                    # Documentation and images
│   └── images/             # Screenshots and demo images
├── sentiment_scraper.py     # Core scraping logic
├── db_handler.py           # Database operations
└── sentiment_analysis_discord_bot.py  # Discord integration
```

---

## ⚙️ Installation

### 1. Prerequisites
* Python 3.x
* Chrome Browser (for Selenium)
* SQLite3 (included with Python)

### 2. Clone and Setup
```bash
git clone https://github.com/yourusername/sentiment_scraper.git
cd sentiment_scraper
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file:
```
DISCORD_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=your_channel_id
SCRAPE_INTERVAL_MINUTES=15
TICKERS=TSLA,SPY,QQQ
```

### 4. Cookie Setup
* Place `stocktwits_cookies.json` in the root directory
* Or run the bot once to generate new cookies

---

## 🧪 Usage

### Single Ticker Analysis
```bash
python sentiment_analysis_discord_bot.py --ticker TSLA
```

### Multi-Ticker Analysis
```bash
python sentiment_analysis_discord_bot.py
```

### Scheduled Mode
The bot automatically runs in scheduled mode with configurable intervals.

---

## 🧪 Testing & Development

### Running Tests
```bash
# Run all tests
pytest tests/

# Run with coverage report
pytest --cov=./ tests/

# Lint check
flake8 .
```

### Development Guidelines
* Follow PEP8 style guide
* Write tests for new features
* Update documentation as needed
* Use type hints for better code clarity

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/<your-feature>`
3. Adhere to [PEP8](https://www.python.org/dev/peps/pep-0008/) and run `flake8`
4. Include unit tests for all new features
5. Submit a pull request with clear commit history

---

## 📌 Roadmap

* [ ] Twitter integration
* [ ] Signal confidence ranking
* [ ] Sentiment-to-price delta model
* [ ] Dashboard for live sentiment feed
* [ ] Reddit integration
* [ ] Enhanced visualization tools

---

## 📄 License & Acknowledgments

Open-source under MIT. Built with ❤️ by Dream.OS.

### Special Thanks
* [TextBlob](https://textblob.readthedocs.io/) for sentiment analysis
* [VADER](https://github.com/cjhutto/vaderSentiment) for sentiment scoring
* [Discord.py](https://discordpy.readthedocs.io/) for Discord integration

---
