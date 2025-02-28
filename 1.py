import sys
import discord
import asyncio
from datetime import datetime, timezone

# Force UTF-8 encoding for Windows terminals
sys.stdout.reconfigure(encoding='utf-8')

def get_embed_color(summary):
    if "Bearish" in summary:
        return discord.Color.red()
    elif "Bullish" in summary:
        return discord.Color.green()
    else:
        return discord.Color.light_gray()

async def test_discord_embed():
    mock_ticker_data = [
        ("📊 TSLA Sentiment Summary", "Total messages: 360\nBullish: 88 (24.4%)\nBearish: 88 (24.4%)\nNeutral: 184 (51.1%)\nAvg. AI Score: 0.042"),
        ("📊 SPY Sentiment Summary", "Total messages: 379\nBullish: 100 (26.4%)\nBearish: 91 (24.0%)\nNeutral: 188 (49.6%)\nAvg. AI Score: 0.053"),
        ("📊 QQQ Sentiment Summary", "Total messages: 385\nBullish: 102 (26.5%)\nBearish: 82 (21.3%)\nNeutral: 201 (52.2%)\nAvg. AI Score: 0.049"),
    ]

    market_summary = (
        "- Bullish: 290 (25.8%)\n"
        "- Bearish: 261 (23.2%)\n"
        "- Neutral: 573 (51.0%)\n"
        "➡️ Overall Market Sentiment: Bullish"
    )

    embed = discord.Embed(
        title="🕵️‍♂️ Overnight Sentiment Summary",
        color=get_embed_color(market_summary),
        timestamp=datetime.now(timezone.utc)
    )
    
    for field_name, field_value in mock_ticker_data:
        embed.add_field(name=field_name, value=field_value, inline=False)
    
    embed.add_field(name="Market Sentiment Summary", value=market_summary, inline=False)
    embed.set_footer(text="Sentiment data updated in real-time.")

    # Print simulated embed output
    print(f"\n{embed.title}\n" + "=" * 40)
    for field in embed.fields:
        print(f"{field.name}\n{field.value}\n" + "-" * 40)
    print(f"Footer: {embed.footer.text}")

asyncio.run(test_discord_embed())
