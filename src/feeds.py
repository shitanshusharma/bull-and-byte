"""Feed configuration for the Bull & Byte digest.

Edit this file to tune what the bot collects:
  - FEEDS:            the curated RSS sources, grouped by category
  - SECTIONS:         display order + human titles for the digest
  - CATEGORY_CAPS:    max items shown per section
  - CATEGORY_KEYWORDS: optional relevance filters (only for the listed categories)

Feed status tags (from a live check on 2026-06-27):
  live   = returned items when checked
  ua     = needs a browser-like User-Agent; some clients get 403/consent/500
  proxy  = Google News proxy, used as a robust fallback

`priority` is used when de-duplicating the same story across sources:
lower number wins (kept), higher number is dropped.
"""

# (category_id, display title) — controls section order in the message.
SECTIONS = [
    ("finance_global", "Global Finance & Markets"),
    ("finance_india", "India Finance & Markets"),
    ("tech", "Tech"),
    ("ai", "AI"),
    ("patterns", "Engineering Deep-Dives"),
]

# Max items shown per section (tune freely).
CATEGORY_CAPS = {
    "finance_global": 6,
    "finance_india": 5,
    "tech": 6,
    "ai": 6,
    "patterns": 4,
}

FEEDS = [
    # --- Global finance / markets ---
    {"category": "finance_global", "name": "CNBC", "priority": 1,
     "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html"},
    {"category": "finance_global", "name": "Financial Times", "priority": 1,
     "url": "https://www.ft.com/rss/home"},
    {"category": "finance_global", "name": "MarketWatch", "priority": 2,
     "url": "http://feeds.marketwatch.com/marketwatch/topstories/"},
    {"category": "finance_global", "name": "Yahoo Finance", "priority": 3,
     "url": "https://finance.yahoo.com/news/rssindex"},
    {"category": "finance_global", "name": "Reuters", "priority": 5,
     "url": "https://news.google.com/rss/search?q=site:reuters.com+business+OR+markets&hl=en-US&gl=US&ceid=US:en"},

    # --- India finance / markets ---
    {"category": "finance_india", "name": "Economic Times", "priority": 1,
     "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"},
    {"category": "finance_india", "name": "LiveMint", "priority": 2,
     "url": "https://www.livemint.com/rss/markets"},
    {"category": "finance_india", "name": "Moneycontrol", "priority": 3,
     "url": "https://www.moneycontrol.com/rss/business.xml"},
    {"category": "finance_india", "name": "Business Standard", "priority": 3,
     "url": "https://www.business-standard.com/rss/markets-106.rss"},
    {"category": "finance_india", "name": "India Markets", "priority": 5,
     "url": "https://news.google.com/rss/search?q=India+stock+market+OR+Sensex+OR+Nifty+OR+RBI+OR+SEBI+when:1d&hl=en-IN&gl=IN&ceid=IN:en"},

    # --- Tech news ---
    {"category": "tech", "name": "TechCrunch", "priority": 1,
     "url": "https://techcrunch.com/feed/"},
    {"category": "tech", "name": "Ars Technica", "priority": 2,
     "url": "https://feeds.arstechnica.com/arstechnica/index"},
    {"category": "tech", "name": "The Verge", "priority": 2,
     "url": "https://www.theverge.com/rss/index.xml"},
    {"category": "tech", "name": "Engadget", "priority": 3,
     "url": "https://www.engadget.com/rss.xml"},
    {"category": "tech", "name": "Hacker News", "priority": 4,
     "url": "https://hnrss.org/frontpage?points=100"},

    # --- AI ---
    {"category": "ai", "name": "VentureBeat AI", "priority": 1,
     "url": "https://venturebeat.com/category/ai/feed/"},
    {"category": "ai", "name": "MIT Tech Review", "priority": 1,
     "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed"},
    {"category": "ai", "name": "The Verge AI", "priority": 2,
     "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"},
    {"category": "ai", "name": "AI Headlines", "priority": 5,
     "url": "https://news.google.com/rss/search?q=AI+OR+%22artificial+intelligence%22+when:1d&hl=en-US&gl=US&ceid=US:en"},

    # --- Engineering design patterns / deep-dives (sparse by nature) ---
    {"category": "patterns", "name": "Martin Fowler", "priority": 1,
     "url": "https://martinfowler.com/feed.atom"},
    {"category": "patterns", "name": "InfoQ", "priority": 2,
     "url": "https://feed.infoq.com/"},
    {"category": "patterns", "name": "dev.to Architecture", "priority": 3,
     "url": "https://dev.to/feed/tag/architecture"},
]

# Optional per-category relevance filters. Only categories listed here are
# filtered; an item is kept if its title/summary matches any keyword (whole
# word, case-insensitive). Categories not listed keep every item.
CATEGORY_KEYWORDS = {
    "ai": [
        "ai", "a.i.", "artificial intelligence", "machine learning", "ml",
        "deep learning", "neural", "llm", "gpt", "chatgpt", "openai",
        "anthropic", "claude", "gemini", "llama", "mistral", "deepmind",
        "transformer", "generative", "inference", "model", "models",
        "agent", "agents", "chatbot", "copilot", "nvidia", "diffusion",
    ],
    "patterns": [
        "architecture", "architect", "design pattern", "design patterns",
        "system design", "scalability", "scalable", "distributed",
        "microservice", "microservices", "monolith", "event-driven",
        "api design", "database", "caching", "cache", "concurrency",
        "observability", "latency", "throughput", "resilience", "refactor",
        "refactoring", "tech debt", "kafka", "kubernetes", "performance",
    ],
}
