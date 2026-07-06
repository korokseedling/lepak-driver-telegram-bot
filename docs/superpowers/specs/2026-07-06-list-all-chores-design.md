# List All Chores — Design

## Problem

`list_outstanding_chores` only returns chores that are `due` or `overdue`. Users have no way to see their full chore list with last-done dates — asking "what are my chores?" returns "nothing outstanding" even when chores exist but simply aren't due yet.

## Solution

Add a new tool function, `list_all_chores`, that returns every chore for a user regardless of status, so the LLM can answer "what chores do I have?" / "show me everything" style questions.

### `chore_manager.list_all(user_id, now=None) -> list[dict]`

- Loads all chores for the user via `load_chores`.
- For each chore, computes:
  - `status` via existing `get_chore_status` (`ok` / `due` / `overdue`)
  - `next_due` = `last_done + interval_days` (ISO date string)
- Returns chores as `{**chore, "status": ..., "next_due": ...}`.
- Sort order: `overdue` chores first, then `due`, then `ok`; within each group, soonest `next_due` first.

### `chore_functions.list_all_chores_tool(user_id) -> str`

- Calls `chore_manager.list_all(user_id)`.
- If no chores exist at all, returns a plain string saying so (e.g. `"No chores tracked yet."`) — no persona, no HTML.
- Otherwise returns one line per chore, plain text, no emoji/HTML:
  ```
  <name> | status: <status> | last_done: <last_done> | next_due: <next_due>
  ```
- This mirrors how the LLM already receives tool output and crafts the final Claptrap-voiced, HTML-formatted reply in the follow-up completion call — the tool itself stays data-only.

### Registration

- Add `list_all_chores` to `TOOL_FUNCTIONS` in `chore_functions.py`.
- Add a matching function schema to `model_config.json` (no parameters beyond `user_id`, which is injected by the dispatch layer, matching the existing `list_outstanding_chores` schema shape).
- Add a line to `system_prompt.md` instructing the LLM to call `list_all_chores` when the user asks to see their full/all chores (vs. `list_outstanding_chores` for due/overdue-only queries), and to format each returned line as an HTML list item in Claptrap's voice.

## Out of scope

- No changes to `list_outstanding_chores`, `add_chore`, `update_chore`, or `complete_chore` behavior.
- No pagination — chore lists are expected to stay small (household chore counts).

## Testing

- Unit test in the style of existing `chore_manager`/`chore_functions` tests: seed a user with a mix of ok/due/overdue chores, assert `list_all` returns all of them in the correct sorted order with correct `next_due` values.
- Test the "no chores" case returns the plain no-chores string.
