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

No LLM and no API keys beyond the Telegram bot token by default. Optional
extras (both off unless configured): one-line **AI summaries** via Groq and
fan-out to **multiple chats/channels**.

---

## How it works

```
RSS feeds -> keep last ~26h -> drop already-sent (state/seen.json)
          -> keyword filter (AI / patterns) -> de-dupe across sources
          -> cap per section -> sectioned HTML digest -> Telegram
          -> record sent items so they never repeat
```

- `src/feeds.py` - the feed list, section order, caps, and keyword filters. **This is the file you tune.**
- `src/` - the package, organized by layer:
  - `config.py` - env knobs and constants.
  - `models/` - typed containers (`Item`, `RunStats`).
  - `utils/` - generic helpers (logging, text tokenization).
  - `core/` - the pipeline stages: `fetch` -> `pipeline` -> `summarize` -> `render`.
  - `delivery/` - Telegram fan-out (`telegram`) and on-disk `state`.
  - `cli.py` - orchestration / entry point.
- `bot.py` - thin entry-point shim (`python bot.py --dry-run` to preview without sending).
- `state/seen.json` - ids of recently sent articles (committed back by the workflow so nothing repeats).
- `state/last_run.json` - machine-readable summary of the most recent run.
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

> To send the **same digest to several chats/channels**, set `TELEGRAM_CHAT_IDS`
> to a comma- or space-separated list (e.g. `-1001,-1002,@mychannel`). Ids from
> `TELEGRAM_CHAT_ID` and `TELEGRAM_CHAT_IDS` are merged and de-duplicated.

### 3. Run it on GitHub (free, scheduled)

1. Push this folder to a GitHub repo.
2. Repo **Settings -> Secrets and variables -> Actions -> New repository secret**, add:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. Open the **Actions** tab, enable workflows, and either wait for the daily run
   or trigger **"Bull and Byte daily digest" -> Run workflow** to test immediately.

The workflow commits the updated `state/seen.json` (and `state/last_run.json`)
after each run so the next digest never repeats stories.

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

All knobs live in `src/feeds.py`:

- **Add / remove sources** - edit `FEEDS` (set `category`, `name`, `url`, `priority`; lower priority wins in de-dupe ties).
- **Items per section** - `CATEGORY_CAPS`.
- **Relevance filters** - `CATEGORY_KEYWORDS` (currently `ai` and `patterns`; add a category to filter it, remove it to keep everything).
- **Section order / titles** - `SECTIONS`.

Runtime knobs in `src/config.py`: `WINDOW_HOURS` (also overridable via
env; falls back to the default if set to a non-positive or non-integer value),
`SEEN_CAP`, `DEDUPE_THRESHOLD`.

**AI summaries (optional):** set `GROQ_API_KEY` (free tier at
[console.groq.com](https://console.groq.com/keys)) to add a one-line summary
under each headline. Pick a model with `GROQ_MODEL` (default
`llama-3.1-8b-instant`) or disable with `AI_SUMMARIES=0`. If the key is missing
or the call fails, the digest is sent without summaries - it never blocks a run.

**Quiet on empty days:** when nothing new is found the bot sends nothing. Pass
`--notify-empty` if you'd rather still receive a "no new items" message.

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
