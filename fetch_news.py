import asyncio
import os

import aiohttp
import feedparser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEED_PATH = os.path.join(BASE_DIR, "feed_list.txt")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RussiaHeatmapBot/1.0)"}

with open(FEED_PATH, "r", encoding="utf-8") as filp:
    RSS_FEEDS = [link.strip() for link in filp if link.strip()]


async def fetch_feed(session, url):
    """Fetch one feed, parse, return list of {title, description}."""
    try:
        async with session.get(url) as response:
            if response.status != 200:
                print(f"  Warning: {response.status} from {url}")
                return []
            # bytes, not text: feedparser sniffs encoding itself (windows-1251 feeds)
            raw = await response.read()

        feed = feedparser.parse(raw)

        # bozo = minor XML issue. Only bail if nothing usable came out.
        if feed.bozo and not feed.entries:
            print(f"  Warning: unparseable feed {url}")
            return []

        articles = [
            {
                "title": entry.get("title", ""),
                "description": entry.get("summary", ""),
            }
            for entry in feed.entries
        ]
        print(f"  -> Found {len(articles)} articles from {url}")
        return articles
    except Exception as e:
        print(f"  Error connecting to {url}: {e}")
        return []


async def get_all_news():
    print(f"Fetching {len(RSS_FEEDS)} news feeds...")
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS) as session:
        results = await asyncio.gather(*(fetch_feed(session, u) for u in RSS_FEEDS))

    articles_list = [a for result in results for a in result]
    print(f"Fetched {len(articles_list)} articles.")
    return {"articles": articles_list}