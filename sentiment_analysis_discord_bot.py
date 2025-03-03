# D:\SocialMediaManager\sentiment_analysis_discord_bot.py

import os
import sys
import asyncio
import glob
import pandas as pd
import logging
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from transformers import pipeline  # Using FinBERT for sentiment analysis
from sentiment_scraper import run_multi_ticker_scraper

# Import the configuration class and create an instance.
from project_config import Config
config = Config()

# Load environment variables explicitly.
def load_discord_credentials():
    """
    Loads Discord credentials from the environment via the centralized config.
    Returns a tuple: (DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID)
    """
    # Retrieve the DISCORD_TOKEN from environment variables
    token = config.get_env("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN not found in environment variables.")

    # Retrieve and cast the DISCORD_CHANNEL_ID to an integer
    try:
        channel_id = config.get_env("DISCORD_CHANNEL_ID", cast_type=int)
        if channel_id <= 0:
            raise ValueError("DISCORD_CHANNEL_ID must be a positive integer.")
    except Exception as e:
        raise ValueError("DISCORD_CHANNEL_ID not found or is invalid in environment variables.") from e
    
    # Return the token and channel ID as a tuple
    return token, channel_id

# Attempt to load the credentials at the module level
try:
    DISCORD_BOT_TOKEN, DISCORD_CHANNEL_ID = load_discord_credentials()
except ValueError as e:
    # Log the error and handle it gracefully
    logger.error(f"Failed to load Discord credentials: {e}")
    # Optionally, re-raise the error if it's critical to stop execution
    raise e


# ------------------ Logging Setup ------------------
from setup_logging import setup_logging
console_level = logging.WARNING  # Show only warnings/errors/critical to console
logger = setup_logging("DiscordBot", log_dir=config.LOG_DIR, console_log_level=console_level)
logger.info("Logger initialized (file logs are verbose, console logs are WARNING and above).")

# ------------------ Discord Bot & Sentiment Analysis ------------------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Load FinBERT sentiment model
finbert = pipeline("text-classification", model="ProsusAI/finbert")

def classify_sentiment(text: str):
    result = finbert(text[:512])
    # Expanded mapping to handle both sets of labels.
    sentiment_map = {
        "positive": "Bullish", 
        "negative": "Bearish", 
        "neutral": "Neutral",
        "bullish": "Bullish",   # new mapping
        "bearish": "Bearish"    # new mapping
    }
    label = result[0]['label'].lower() if result[0].get('label') else "neutral"
    return sentiment_map.get(label, "Neutral"), result[0]['score']


# ------------------ Embed Helper Functions ------------------
def get_embed_color(summary):
    """Determines embed color based on sentiment text."""
    color_map = {
        "Bullish": 0x57F287,  # Discord green
        "Bearish": 0xED4245,  # Discord red
        "Neutral": 0x979C9F   # Discord gray
    }
    return discord.Color(color_map.get(summary, 0x000000))

def create_embed(description, color):
    """
    Creates a Discord embed message for better visualization.
    """
    embed = discord.Embed(description=description, color=color)
    
    # Split long descriptions into multiple fields
    max_chunk_size = 1024
    chunks = [description[i: i + max_chunk_size] for i in range(0, len(description), max_chunk_size)]
    for i, chunk in enumerate(chunks):
        embed.add_field(
            name=f"Part {i+1}" if len(chunks) > 1 else "Summary",
            value=chunk,
            inline=False
        )
    embed.set_footer(text="Sentiment data updated in real-time.")
    return embed

# ------------------ Bot Commands ------------------
@bot.command(name="sentiment")
async def sentiment_command(ctx, ticker: str = "TSLA"):
    """
    Aggregates real-time sentiment for a given ticker by reading CSV files.
    """
    csv_files = glob.glob(f"**/{ticker}_*_sentiment.csv", recursive=True)
    if not csv_files:
        await ctx.send(f"❌ No sentiment data found for **{ticker}**.")
        return

    try:
        df_list = [pd.read_csv(f) for f in csv_files]
        df = pd.concat(df_list, ignore_index=True)
    except Exception as e:
        logger.error(f"Error reading CSV for {ticker}: {e}")
        await ctx.send(f"⚠️ Error fetching sentiment data for **{ticker}**.")
        return

    if df.empty:
        await ctx.send(f"❌ No sentiment data available for **{ticker}**.")
        return

    total_msgs = len(df)
    bullish = len(df[df["sentiment_category"] == "Bullish"])
    bearish = len(df[df["sentiment_category"] == "Bearish"])
    neutral = len(df[df["sentiment_category"] == "Neutral"])

    bullish_pct = (bullish / total_msgs) * 100 if total_msgs else 0
    bearish_pct = (bearish / total_msgs) * 100 if total_msgs else 0
    neutral_pct = (neutral / total_msgs) * 100 if total_msgs else 0

    overall_sentiment = (
        "📈 Bullish" if bullish > bearish 
        else "📉 Bearish" if bearish > bullish 
        else "⚖ Neutral"
    )

    description = (
        f"**Total Messages:** {total_msgs}\n"
        f"**🟢 Bullish:** {bullish} ({bullish_pct:.1f}%)\n"
        f"**🔴 Bearish:** {bearish} ({bearish_pct:.1f}%)\n"
        f"**⚪ Neutral:** {neutral} ({neutral_pct:.1f}%)\n"
        f"**Overall Sentiment:** {overall_sentiment}"
    )

    color = get_embed_color(overall_sentiment)
    embed = create_embed(description, color)
    await ctx.send(embed=embed)

# ------------------ Automated Overnight Scraper ------------------
async def overnight_scraper_scheduler():
    """
    Runs the ephemeral-based multi-ticker sentiment scraper and posts updates to Discord.
    """
    tickers = ["TSLA", "SPY", "QQQ"]
    async for embed in run_multi_ticker_scraper(tickers=tickers, interval_minutes=15, run_duration_hours=24):
        channel = bot.get_channel(DISCORD_CHANNEL_ID)
        if not channel:
            try:
                channel = await bot.fetch_channel(DISCORD_CHANNEL_ID)
            except Exception as e:
                logger.error(f"Failed to fetch Discord channel: {e}")
                continue
        try:
            await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send Discord message: {e}")

# ------------------ Bot Event Handlers ------------------
@bot.event
async def on_ready():
    logger.info(f"✅ Discord bot connected as {bot.user}")
    bot.loop.create_task(overnight_scraper_scheduler())

if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN)
