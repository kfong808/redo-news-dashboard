"""
Pulls ecommerce news from a list of RSS feeds + Google News searches.
Returns a deduplicated list of stories.
"""

import re
import feedparser
from urllib.parse import quote


# Always-on news sources. Each tuple is (display_name, rss_url).
FEEDS = [
    ("Practical Ecommerce", "https://www.practicalecommerce.com/feed"),
    ("Modern Retail",       "https://www.modernretail.co/feed/"),
    ("Retail Dive",         "https://www.retaildive.com/feeds/news/"),
    ("eCommerce Bytes",     "https://www.ecommercebytes.com/cab/abn/category/ec.rss"),
    ("Hacker News",         "https://news.ycombinator.com/rss"),
    ("r/shopify",           "https://www.reddit.com/r/shopify/.rss"),
    ("r/ecommerce",         "https://www.reddit.com/r/ecommerce/.rss"),
]


# Google News RSS searches. One feed gets created per term.
GOOGLE_NEWS_TERMS = [
    "Klaviyo",
    "Yotpo",
    "Loop Returns",
    "Attentive",
    "Omnisend",
    "Postscript",
    "Shopify",
    "Mailchimp",
    "ShipStation",
    "Narvar",
    "agentic commerce",
    "AI shopping agent",
    "post-purchase ecommerce",
    "abandoned cart recovery",
    "DTC ecommerce",
    "ecommerce SaaS",
    "Shopify Plus",
    "returns management software",
    "headless commerce",
]


def google_news_url(term):
    """Build a Google News RSS URL for a search term."""
    return ("https://news.google.com/rss/search?q="
            + quote(term)
            + "&hl=en-US&gl=US&ceid=US:en")


def clean_summary(html):
    """Strip HTML tags from an RSS summary and cap length."""
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:500]


def parse_feed(source, url, cap=15):
    """Parse a single RSS feed. Returns a list of normalized story dicts."""
    out = []
    try:
        d = feedparser.parse(url)
        for entry in d.entries[:cap]:
            title = (entry.get("title") or "").strip()
            link = entry.get("link") or ""
            if not title or not link:
                continue
            out.append({
                "title": title,
                "url": link,
                "source": source,
                "published": entry.get("published") or entry.get("updated") or "",
                "summary": clean_summary(entry.get("summary") or entry.get("description") or ""),
            })
    except Exception as exc:
        print(f"  ! error fetching {source}: {exc}")
    return out


def dedupe(items):
    """Remove duplicates by URL (or by title if URL is missing)."""
    seen = set()
    out = []
    for it in items:
        key = (it.get("url") or it.get("title") or "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(it)
    return out


def fetch_all():
    """Pull every feed + every Google News search. Returns deduped list."""
    items = []

    print(f"Fetching {len(FEEDS)} core feeds...")
    for name, url in FEEDS:
        chunk = parse_feed(name, url, cap=20)
        items.extend(chunk)
        print(f"  {name}: {len(chunk)} items")

    print(f"Fetching {len(GOOGLE_NEWS_TERMS)} Google News searches...")
    for term in GOOGLE_NEWS_TERMS:
        chunk = parse_feed(f"Google News: {term}", google_news_url(term), cap=10)
        items.extend(chunk)

    items = dedupe(items)
    print(f"Total after dedupe: {len(items)} items")
    return items


if __name__ == "__main__":
    import json
    items = fetch_all()
    print(json.dumps(items[:3], indent=2, ensure_ascii=False))
