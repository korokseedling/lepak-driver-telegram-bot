# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claptrap Chore Bot is a Telegram chore-tracking assistant with the personality of Claptrap (Borderlands) — zany, self-aggrandizing, Napoleon complex, addresses the user as "minion." Users manage recurring chores through natural language chat: check outstanding chores, get proactively notified when a chore has gone too long without being done, set up new recurring chores, and log remarks when marking a chore complete. The bot uses OpenAI's GPT-4o-mini with function calling for natural language processing and maintains conversation history per user per day.

This project is being migrated from an earlier bus/carpark assistant ("Lepak Driver"). The Telegram + OpenAI function-calling scaffolding is being kept; the domain logic is being replaced with chore tracking. See `docs/superpowers/specs/2026-07-06-claptrap-chore-bot-design.md` for the full design spec and `docs/superpowers/plans/` for the implementation plan once written.

## Key Commands

### Development & Testing
```bash
# Run the bot locally
python bot.py

# Test setup and API connectivity
python test_setup.py

# Install dependencies
pip install -r requirements.txt
```

### Production Deployment
```bash
# Deploy to Railway
git push origin main  # Auto-deploys via Procfile: worker: python bot.py
```

### Environment Variables Required
- `TELEGRAM_TOKEN` - From @BotFather
- `OPENROUTER_API_KEY` - OpenRouter API access (routes to GPT-4o-mini via OpenRouter)

(`LTA_API_KEY` is no longer required — it was only used by the retired bus/carpark domain logic.)

## Architecture

### Core Components

**bot.py** - Main application entry point
- Telegram bot handlers and message processing
- OpenAI function calling integration
- Conversation history management (20 messages per user per day)
- Environment variable validation with detailed Railway debugging
- Asterisk-to-HTML conversion for Telegram formatting
- Daily `JobQueue` job that scans all users' chore files and proactively messages anyone with due or overdue chores

**chore_manager.py** - Chore persistence and business logic
- CRUD for chores, stored one JSON file per user in `chores/`
- Overdue/due computation: a chore is *due* once `now >= last_done + interval_days`, and *overdue* once `now >= last_done + interval_days + grace_days`
- Completion history log (timestamp + optional remark) per chore

**chore_functions.py** - OpenAI function implementations
- `add_chore(name, interval_days, grace_days=3)` - create a new recurring chore
- `list_outstanding_chores()` - list chores that are due or overdue
- `list_all_chores()` - list every chore regardless of status, with last-done and next-due dates; returns final HTML/persona text directly, same as the other tools
- `complete_chore(name, remark=None)` - mark a chore done now, optionally logging a remark
- `update_chore(name, interval_days=None, grace_days=None)` - change an existing chore's interval/grace settings
- Telegram HTML formatting for all responses, built via `response_templates.py` (see below) — no LLM rephrasing involved

**response_templates.py** - Local persona templating
- Each chore function's success/error message is built by picking from a pool of 10 pregenerated Claptrap-voiced phrasings and interpolating the real chore data (name, interval, grace, remark, error detail)
- `format_friendly_date(iso_str)` renders stored ISO timestamps (`last_done`, `next_due`) as reader-friendly dates (e.g. "6 Jul 2026") everywhere a chore date is shown to the user
- A shuffle-bag picker per template pool guarantees all 10 phrasings are used before any repeat, for response diversity without needing a second LLM call
- Replaces what used to be a second OpenAI API call that rephrased tool output into persona — removing it roughly halves per-message latency on any chore-related request

**model_config.json** - Configuration
- OpenAI model settings (GPT-4o-mini via OpenRouter, temperature: 0.7)
- Tool function definitions for the 5 chore functions above

**system_prompt.md** - Bot personality and formatting rules
- Claptrap persona: zany, boastful, Napoleon complex, calls the user "minion" — but chore facts reported must stay accurate, no exaggerating what's overdue
- Strict HTML formatting requirements (no asterisks) — only relevant to the no-tool-call chat path now, since tool responses are templated locally and never round-trip through the model
- Guidance on when to call each of the 5 chore functions

### Data Flow

1. **User message** → Telegram → `handle_message()`
2. **Load conversation** history from `conversations/` directory
3. **OpenAI processing** with system prompt (Claptrap) + history + chore tool schemas — this single call both decides whether/which tool to call and, for plain chat with no tool call, produces the final reply directly
4. **Function calling** (if a tool was chosen) invokes `chore_functions.py`, which reads/writes `chores/chore_<user_id>.json` via `chore_manager.py` and returns an already persona-formatted response via `response_templates.py` — no second OpenAI call
5. **Response formatting** with HTML tags (convert asterisks as fallback)
6. **Save conversation** and send reply

### Chore Data Model

One JSON file per user: `chores/chore_<user_id>.json`

```json
{
  "chat_id": 123456789,
  "chores": [
    {
      "id": "water-plants",
      "name": "Water plants",
      "interval_days": 3,
      "grace_days": 3,
      "last_done": "2026-07-04T10:00:00",
      "created_at": "2026-06-01T09:00:00",
      "history": [
        {"date": "2026-07-04T10:00:00", "remark": "used less water today"}
      ]
    }
  ]
}
```

- `id` is a slugified `name` (lowercase, spaces→hyphens, non-alphanumerics stripped), unique per user — used to look up a chore when the LLM passes back a name for `complete_chore`/`update_chore`.
- `chat_id` is captured on first message (private chats only) so the daily job can push notifications without depending on the LLM path.
- A new chore's `last_done` is set to `created_at` at creation time, so the interval starts counting immediately.

### Daily Due/Overdue Notification

A `JobQueue.run_daily` job (registered at bot startup, `check_chore_status_job` in `bot.py`) scans every file in `chores/` once per day and sends a proactive Telegram message, in Claptrap's voice, to any user with a **due** or **overdue** chore. `chore_functions.format_daily_notification()` builds one combined message per user: a "heads up" section for chores that just became due, and a louder nagging section for chores past their grace period — either section is omitted if empty. One bad/corrupt user file must not stop the job from processing the rest.

### Key Features

- **Conversation persistence**: Daily conversation files with 20-message limit
- **Recurring chore tracking**: interval + configurable grace period per chore
- **Proactive notifications**: daily scan pushes due and overdue chores to affected users
- **Error handling**: not-found/duplicate/invalid-args cases return clear errors the LLM relays in-persona
- **HTML formatting**: All responses use HTML tags, never asterisks
- **Auto-cleanup**: Old conversation files (>7 days) cleaned on startup

### File Structure Details

- `chores/` - Per-user chore data (auto-created), one JSON file per user
- `conversations/` - Per-user daily conversation history (auto-created)
- `Procfile` - Railway deployment configuration
- `requirements.txt` - Python dependencies (`python-telegram-bot[job-queue]`, openai, requests)
- `docs/superpowers/specs/` - Design specs (see `2026-07-06-claptrap-chore-bot-design.md` for this feature)
- `docs/superpowers/plans/` - Implementation plans

### Common Development Patterns

When adding new functionality:
- Add tool function to `chore_functions.py` and register in the tool-function dispatch table
- Define tool schema in `model_config.json`
- Use HTML formatting (`<b>`, `<i>`, `<code>`) never asterisks
- Keep chore facts accurate even though the persona is exaggerated — don't let Claptrap's voice invent or inflate chore data
- Not-found/invalid-arg errors should surface the user's actual chore names so the LLM can ask for clarification rather than guessing

### Deployment Notes

The bot is designed for Railway deployment with extensive environment variable debugging. All API keys are validated on startup with detailed error messages for troubleshooting Railway configuration issues.

**Persistent storage:** Railway's container filesystem is ephemeral by default — every redeploy starts from a fresh disk, wiping `chores/` and `conversations/`. To keep chore data across redeploys, attach a Railway Volume mounted at `/app/chores` (Railway dashboard → service → Settings → Volumes). `conversations/` is intentionally left unmounted since it's daily/disposable data with its own 7-day auto-cleanup. Without the volume, users have to re-add all their chores after every `git push` to `main`.
