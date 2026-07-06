# Claptrap Chore Bot — Design Spec

## Summary

Repurpose the existing "Lepak Driver" Telegram bot codebase (Telegram + OpenAI GPT-4o-mini function-calling scaffolding) into a new chore-tracking bot with a "Claptrap" (Borderlands) personality. The bus/carpark domain logic (LTA DataMall integration) is fully removed. In its place: a recurring-chore tracker with natural-language interaction, per-user JSON persistence, and daily proactive overdue notifications.

## Goals

- Users can, via natural Telegram chat:
  - Check outstanding chores (due or overdue)
  - Set up a new recurring chore (with interval and optional grace period)
  - Mark a chore as done, optionally with a remark
  - Update an existing chore's interval/grace settings
- Bot proactively notifies users once daily about chores that are overdue (past interval + grace).
- Bot personality: Claptrap from Borderlands — zany, self-aggrandizing, Napoleon complex, addresses the user as "minion." Personality is loud but the underlying chore data/answers must remain accurate.
- Supports multiple independent users, each with their own chore list.

## Non-Goals

- No LTA bus/carpark functionality (fully removed, not preserved behind a flag).
- No group chat support — proactive notifications assume one chat_id per user (private chat).
- No chore deletion function (not requested — can be added later if needed).
- No configurable notification check frequency per chore — single daily job for all users.

## Architecture

Keep the existing Telegram + OpenAI function-calling architecture from `bot.py` (message handling loop, per-user daily conversation history, HTML-formatting-only output, env var validation). Replace the domain-specific layer:

| Old (Lepak Driver) | New (Claptrap Chore Bot) |
|---|---|
| `lta_integration.py` | `chore_manager.py` |
| `tool_functions.py` | `chore_functions.py` |
| `bus_stops_singapore.json` | *(removed, no replacement needed)* |
| `conversations/` (unchanged) | `conversations/` (unchanged) |
| — | `chores/` (new) |
| `model_config.json` (bus/carpark tool schemas) | `model_config.json` (chore tool schemas) |
| `system_prompt.md` (Singaporean driver assistant) | `system_prompt.md` (Claptrap persona) |

### Data Flow (unchanged shape, new domain)

1. User message → Telegram → `handle_message()`
2. Load conversation history from `conversations/`
3. OpenAI processing with system prompt (Claptrap) + history + chore tool schemas
4. Function calling triggers `chore_functions.py` → `chore_manager.py` (reads/writes `chores/chore_<user_id>.json`)
5. Response formatted as Telegram HTML (asterisk-to-HTML fallback conversion retained)
6. Save conversation, send reply

### New: Daily Overdue Check

A `JobQueue.run_daily` job (registered in `bot.py` at startup) runs once per day:
1. Scans every file in `chores/`
2. For each user, computes overdue chores (see "Overdue Logic" below)
3. If any overdue chores exist, sends a proactive `bot.send_message(chat_id, ...)` in Claptrap's voice listing them

`python-telegram-bot`'s JobQueue requires the `job-queue` extra (pulls in APScheduler) — `requirements.txt` needs `python-telegram-bot[job-queue]==20.7` instead of the bare package.

## Data Model

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

- `id`: slugified `name`, unique per user, used to look up a chore for `complete_chore`/`update_chore` when the LLM passes back a name.
- `chat_id`: captured on first message from the user (private chat, so `chat_id == user_id`), used for proactive push targeting without depending on the LLM path.
- `history`: append-only log of completions; each entry has a timestamp and optional remark (null if none given).

### Overdue Logic

- `due_at = last_done + interval_days`
- Chore is **due** (not yet overdue) once `now >= due_at`
- Chore is **overdue** once `now >= due_at + grace_days`
- `list_outstanding_chores()` returns both due and overdue chores (labeled distinctly)
- The daily proactive job only messages users about **overdue** chores (avoids nagging during the grace window)
- A brand-new chore (no `last_done` yet) is never due/overdue — `last_done` is set to `created_at` at creation time so the interval starts counting immediately

## OpenAI Function Schemas (`model_config.json`)

Four tool functions, replacing all existing bus/carpark tools:

1. **`add_chore(name: str, interval_days: int, grace_days: int = 3)`**
   Creates a new chore for the user. Errors if a chore with the same (slugified) name already exists for that user — tells the LLM to use `update_chore` instead.

2. **`list_outstanding_chores()`**
   No parameters. Returns all chores that are due or overdue, with days-since-last-done and status (`due` vs `overdue`). Returns a friendly "nothing outstanding" result if none.

3. **`complete_chore(name: str, remark: str = None)`**
   Looks up chore by slugified name for the user. Sets `last_done` to now, appends a `history` entry (with remark if provided). Errors if no chore with that name exists, listing the user's current chore names to help the LLM disambiguate.

4. **`update_chore(name: str, interval_days: int = None, grace_days: int = None)`**
   Looks up chore by slugified name. Updates whichever of `interval_days`/`grace_days` is provided (at least one must be non-null). Errors if chore not found or if both params are omitted.

## Persona (`system_prompt.md`)

Rewritten as Claptrap (Borderlands):
- Addresses the user as "minion"
- Zany, boastful, self-aggrandizing tone with a Napoleon complex (loudly overcompensates, claims grandeur despite being "just a small robot")
- Despite the personality, chore facts reported to the user must be accurate — no exaggerating overdue counts or inventing chores
- Retains the existing hard requirement: all Telegram output uses HTML tags (`<b>`, `<i>`, `<code>`), never markdown asterisks — this is a formatting constraint independent of persona and must not be relaxed
- Drop all bus-stop/two-step-workflow instructions from the old prompt; replace with guidance on when to call each of the 4 chore functions

## Error Handling

- Chore not found (`complete_chore`/`update_chore`): return an error result listing the user's actual chore names, so the LLM can ask the user to clarify rather than guessing.
- Duplicate chore name (`add_chore`): return an error suggesting `update_chore`.
- Invalid function args (e.g. `interval_days <= 0`, both params omitted in `update_chore`): validated in `chore_manager.py`, return a clear error string back through the tool-call result (LLM relays it in-persona).
- Corrupt/missing `chores/chore_<user_id>.json`: treated as "no chores yet" (fresh empty state), matching the existing conversation-history file handling pattern in `bot.py`.
- Daily job: wrap the per-user scan loop so one user's bad file doesn't stop the job from processing the rest; log and continue.

## Testing Approach

- Unit-test `chore_manager.py` directly (no Telegram/OpenAI dependency): create/read/update chore files in a temp directory, verify overdue-logic boundary conditions (exactly at `due_at`, exactly at `due_at + grace_days`, just before each).
- Unit-test `chore_functions.py` wrapper functions against a temp `chores/` dir, verifying correct error strings for not-found/duplicate/invalid-args cases.
- Manual end-to-end test via `test_setup.py` (updated) — verify env vars, then a scripted conversation: add chore → list outstanding (empty) → fast-forward by editing `last_done` in the JSON → list outstanding (shows due) → complete with remark → verify history.
- Manually trigger the daily job function directly (not waiting for the schedule) to verify the overdue-scan and message format during development.

## Removed Files

- `lta_integration.py`
- `tool_functions.py`
- `bus_stops_singapore.json`
- `lepak_driver_bot.log` (stale log, regenerated under new bot identity — safe to delete)

## Open Items for Implementation Plan

- Exact daily job trigger time (default to a reasonable fixed hour, e.g. 9:00 AM local/server time — not user-configurable in this iteration).
- Slugification rule for chore `id` (lowercase, spaces→hyphens, strip non-alphanumerics) — needs to be defined once, shared between `add_chore` lookup and `complete_chore`/`update_chore` lookup.
