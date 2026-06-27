# Bull & Byte

A tiny, self-hosted Telegram bot that pushes one **daily digest** of tech +
finance news. It pulls a curated set of RSS feeds, removes noise (time window,
de-duplication, per-category caps), and delivers a clean sectioned message via
the Telegram Bot API. It runs for free on a GitHub Actions cron - no server.

Sections in each digest:

- **Global Finance & Markets** - CNBC, Financial Times, MarketWatch, Yahoo Finance, Reuters
- **India Finance & Markets** - Economic Times, LiveMint, Moneycontrol, Business Standard
- **Tech** - TechCrunch, Ars Technica, The Verge, Engadget, Hacker News
- **AI** - VentureBeat AI, MIT Technology Review, The Verge AI, AI headlines
- **Engineering Deep-Dives** - Martin Fowler, InfoQ, dev.to (architecture)

No LLM, no API keys beyond the Telegram bot token.

---

## How it works

```
RSS feeds -> keep last ~26h -> drop already-sent (state/seen.json)
          -> keyword filter (AI / patterns) -> de-dupe across sources
          -> cap per section -> sectioned HTML digest -> Telegram
          -> record sent items so they never repeat
```

- `feeds.py` - the feed list, section order, caps, and keyword filters. **This is the file you tune.**
- `bot.py` - the pipeline above (`--dry-run` to preview without sending).
- `state/seen.json` - ids of recently sent articles (committed back by the workflow so nothing repeats).
- `.github/workflows/digest.yml` - the daily schedule.

---

## Setup

### 1. Create the Telegram bot

1. In Telegram, message [@BotFather](https://t.me/BotFather) -> `/newbot` -> follow prompts.
2. Copy the **bot token** it gives you (looks like `123456:ABC-DEF...`).

### 2. Find your chat id

1. Send any message to your new bot (e.g. "hi").
2. Open this URL in a browser (paste your token):
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Find `"chat":{"id":<NUMBER>...}` - that number is your `TELEGRAM_CHAT_ID`.
   (Alternatively, message [@userinfobot](https://t.me/userinfobot).)

> To post to a **channel** instead, add the bot as an admin and use the channel's
> `@username` or numeric id as `TELEGRAM_CHAT_ID`.

### 3. Run it on GitHub (free, scheduled)

1. Push this folder to a GitHub repo.
2. Repo **Settings -> Secrets and variables -> Actions -> New repository secret**, add:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. Open the **Actions** tab, enable workflows, and either wait for the daily run
   or trigger **"Bull and Byte daily digest" -> Run workflow** to test immediately.

The workflow commits the updated `state/seen.json` after each run so the next
digest never repeats stories.

---

## Run locally

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt

# Preview the digest without sending anything:
python bot.py --dry-run
```

To send for real locally, copy `.env.example` to `.env`, fill in the two values,
then run `python bot.py`. (`.env` is git-ignored.)

---

## Tuning

All knobs live in `feeds.py`:

- **Add / remove sources** - edit `FEEDS` (set `category`, `name`, `url`, `priority`; lower priority wins in de-dupe ties).
- **Items per section** - `CATEGORY_CAPS`.
- **Relevance filters** - `CATEGORY_KEYWORDS` (currently `ai` and `patterns`; add a category to filter it, remove it to keep everything).
- **Section order / titles** - `SECTIONS`.

Runtime knobs in `bot.py` (top of file): `WINDOW_HOURS` (also overridable via env),
`SEEN_CAP`, `DEDUPE_THRESHOLD`.

**Change the schedule:** edit the `cron` line in
`.github/workflows/digest.yml`. It uses UTC - `0 3 * * *` is 08:30 IST. Add more
`- cron:` lines for multiple daily runs.

---

## Notes & limitations

- A few feeds (Moneycontrol, Business Standard, The Verge, Engadget, InfoQ) block
  default HTTP clients; the bot sends a browser-like User-Agent to work around
  this. Any feed that still fails is skipped (non-fatal) and logged.
- Cross-source de-duplication is title-similarity based, so it is approximate -
  occasional near-duplicates or misses are possible (acceptable trade-off for a
  no-LLM build).
- The "Engineering Deep-Dives" sources update slowly; that section may be short
  or empty some days - expected.
- GitHub's scheduled Actions can start a few minutes late and are paused after
  ~60 days of repo inactivity (just push a commit or run manually to resume).
- Premium outlets (Bloomberg, WSJ) have no free full-text RSS; Reuters is pulled
  via a Google News proxy for the same reason.

---

## Credit

The Telegram send approach (Bot API `sendMessage` with HTML + 429 `retry_after`
handling) is adapted from the relay in
[koala73/worldmonitor](https://github.com/koala73/worldmonitor). This project is
a standalone bot, not a fork.
