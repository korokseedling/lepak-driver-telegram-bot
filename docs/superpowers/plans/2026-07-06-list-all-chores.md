# List All Chores Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `list_all_chores` tool so the bot can answer "what chores do I have?" / "show me everything" by returning every chore (not just due/overdue ones) with status and next-due date.

**Architecture:** A new `chore_manager.list_all()` function computes status + next_due for every chore and sorts by urgency. A new `chore_functions.list_all_chores_tool()` wraps it as a plain-text (no persona/HTML) tool response, registered in `TOOL_FUNCTIONS`. `model_config.json` gets a matching function schema, and `system_prompt.md` tells the LLM when to call it and how to format the plain-text output into Claptrap's voice.

**Tech Stack:** Python, pytest, existing `chore_manager`/`chore_functions` modules.

## Global Constraints

- Interval and grace period are always in whole days (existing convention, unchanged).
- Tool functions that feed the LLM's follow-up completion call return plain, unstyled text — no emoji, no HTML, no persona. The LLM (via `system_prompt.md`) is responsible for voice and HTML formatting, per the spec's approved design.
- Follow existing test patterns: `isolate_chores_dir` autouse fixture via `monkeypatch.setattr(chore_manager, "CHORES_DIR", str(tmp_path))`.
- No pagination — chore lists are expected to stay small.

---

### Task 1: `chore_manager.list_all()`

**Files:**
- Modify: `chore_manager.py` (add function after `list_outstanding`, i.e. after line 149)
- Test: `test_chore_manager.py` (add tests after `test_list_outstanding_returns_due_and_overdue_with_status`, i.e. after line 160)

**Interfaces:**
- Consumes: `chore_manager.load_chores(user_id)`, `chore_manager.get_chore_status(chore, now)` (both already exist, unchanged).
- Produces: `chore_manager.list_all(user_id, now=None) -> list[dict]`. Each dict is `{**chore, "status": <"ok"|"due"|"overdue">, "next_due": <ISO date string>}`. Sorted: overdue chores first, then due, then ok; within each group, ascending by `next_due`. Later tasks (`chore_functions.list_all_chores_tool`) call this and rely on this exact sort order and these exact keys.

- [ ] **Step 1: Write the failing tests**

Add to `test_chore_manager.py` (after `test_list_outstanding_returns_due_and_overdue_with_status`, currently ending at line 160):

```python
def test_list_all_includes_ok_due_and_overdue_chores():
    now = datetime(2026, 7, 6, 12, 0, 0)
    chore_manager.add_chore("123", "Fresh chore", interval_days=3)
    chore_manager.add_chore("123", "Overdue chore", interval_days=3, grace_days=3)

    data = chore_manager.load_chores("123")
    for chore in data["chores"]:
        if chore["name"] == "Overdue chore":
            chore["last_done"] = (now - timedelta(days=6)).isoformat()
    chore_manager.save_chores("123", data)

    all_chores = chore_manager.list_all("123", now)

    assert len(all_chores) == 2
    names_and_status = {c["name"]: c["status"] for c in all_chores}
    assert names_and_status == {"Fresh chore": "ok", "Overdue chore": "overdue"}


def test_list_all_computes_next_due_as_last_done_plus_interval():
    now = datetime(2026, 7, 6, 12, 0, 0)
    last_done = now - timedelta(days=1)
    chore_manager.add_chore("123", "Water plants", interval_days=3)
    data = chore_manager.load_chores("123")
    data["chores"][0]["last_done"] = last_done.isoformat()
    chore_manager.save_chores("123", data)

    all_chores = chore_manager.list_all("123", now)

    expected_next_due = (last_done + timedelta(days=3)).isoformat()
    assert all_chores[0]["next_due"] == expected_next_due


def test_list_all_sorts_overdue_then_due_then_ok():
    now = datetime(2026, 7, 6, 12, 0, 0)
    chore_manager.add_chore("123", "OK chore", interval_days=10)
    chore_manager.add_chore("123", "Due chore", interval_days=3, grace_days=3)
    chore_manager.add_chore("123", "Overdue chore", interval_days=3, grace_days=3)

    data = chore_manager.load_chores("123")
    for chore in data["chores"]:
        if chore["name"] == "Due chore":
            chore["last_done"] = (now - timedelta(days=3)).isoformat()
        if chore["name"] == "Overdue chore":
            chore["last_done"] = (now - timedelta(days=6)).isoformat()
    chore_manager.save_chores("123", data)

    all_chores = chore_manager.list_all("123", now)

    assert [c["name"] for c in all_chores] == ["Overdue chore", "Due chore", "OK chore"]


def test_list_all_sorts_by_next_due_within_same_status_group():
    now = datetime(2026, 7, 6, 12, 0, 0)
    chore_manager.add_chore("123", "OK chore far", interval_days=20)
    chore_manager.add_chore("123", "OK chore near", interval_days=10)

    all_chores = chore_manager.list_all("123", now)

    assert [c["name"] for c in all_chores] == ["OK chore near", "OK chore far"]


def test_list_all_returns_empty_list_when_no_chores():
    assert chore_manager.list_all("123") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest test_chore_manager.py -v -k list_all`
Expected: FAIL with `AttributeError: module 'chore_manager' has no attribute 'list_all'`

- [ ] **Step 3: Implement `list_all` in `chore_manager.py`**

Add after `list_outstanding` (currently lines 142-149):

```python
def list_all(user_id, now: datetime = None) -> list:
    if now is None:
        now = datetime.now()
    data = load_chores(user_id)

    _status_rank = {"overdue": 0, "due": 1, "ok": 2}
    result = []
    for chore in data["chores"]:
        status = get_chore_status(chore, now)
        last_done = datetime.fromisoformat(chore["last_done"])
        next_due = (last_done + timedelta(days=chore["interval_days"])).isoformat()
        result.append({**chore, "status": status, "next_due": next_due})

    result.sort(key=lambda c: (_status_rank[c["status"]], c["next_due"]))
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest test_chore_manager.py -v`
Expected: all tests PASS (including the pre-existing ones — confirms no regression)

- [ ] **Step 5: Commit**

```bash
git add chore_manager.py test_chore_manager.py
git commit -m "$(cat <<'EOF'
Add chore_manager.list_all for full chore listing

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `chore_functions.list_all_chores_tool()`

**Files:**
- Modify: `chore_functions.py` (add function after `list_outstanding_chores_tool`, i.e. after line 22; add to `TOOL_FUNCTIONS` dict at the bottom)
- Test: `test_chore_functions.py` (add tests after `test_list_outstanding_chores_tool_lists_overdue_chore`, i.e. after line 46)

**Interfaces:**
- Consumes: `chore_manager.list_all(user_id)` from Task 1 — exact keys `name`, `status`, `last_done`, `next_due` per returned dict.
- Produces: `chore_functions.list_all_chores_tool(user_id) -> str`, registered under `TOOL_FUNCTIONS['list_all_chores']`. Plain text, one chore per line: `"<name> | status: <status> | last_done: <last_done> | next_due: <next_due>"`. If no chores exist, returns exactly `"No chores tracked yet."`.

- [ ] **Step 1: Write the failing tests**

Add to `test_chore_functions.py` (after `test_list_outstanding_chores_tool_lists_overdue_chore`, currently ending at line 46):

```python
def test_list_all_chores_tool_reports_no_chores():
    result = chore_functions.TOOL_FUNCTIONS['list_all_chores'](user_id="123")

    assert result == "No chores tracked yet."


def test_list_all_chores_tool_lists_every_chore_plain_text():
    chore_functions.TOOL_FUNCTIONS['add_chore'](user_id="123", name="Water plants", interval_days=3)
    chore_functions.TOOL_FUNCTIONS['add_chore'](user_id="123", name="Vacuum", interval_days=7)

    result = chore_functions.TOOL_FUNCTIONS['list_all_chores'](user_id="123")

    assert "Water plants | status: ok | last_done:" in result
    assert "Vacuum | status: ok | last_done:" in result
    assert "next_due:" in result
    # Plain data only — no persona or HTML formatting from the tool itself
    assert "<b>" not in result
    assert "minion" not in result.lower()


def test_list_all_chores_tool_shows_overdue_status():
    chore_manager.add_chore("123", "Water plants", interval_days=3, grace_days=3)
    data = chore_manager.load_chores("123")
    data["chores"][0]["last_done"] = (datetime.now() - timedelta(days=10)).isoformat()
    chore_manager.save_chores("123", data)

    result = chore_functions.TOOL_FUNCTIONS['list_all_chores'](user_id="123")

    assert "status: overdue" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest test_chore_functions.py -v -k list_all`
Expected: FAIL with `KeyError: 'list_all_chores'`

- [ ] **Step 3: Implement `list_all_chores_tool` in `chore_functions.py`**

Add after `list_outstanding_chores_tool` (currently lines 14-22):

```python
def list_all_chores_tool(user_id):
    all_chores = chore_manager.list_all(user_id)
    if not all_chores:
        return "No chores tracked yet."

    lines = []
    for chore in all_chores:
        lines.append(
            f"{chore['name']} | status: {chore['status']} | "
            f"last_done: {chore['last_done']} | next_due: {chore['next_due']}"
        )
    return "\n".join(lines)
```

Update `TOOL_FUNCTIONS` at the bottom of the file:

```python
TOOL_FUNCTIONS = {
    'add_chore': add_chore_tool,
    'list_outstanding_chores': list_outstanding_chores_tool,
    'list_all_chores': list_all_chores_tool,
    'complete_chore': complete_chore_tool,
    'update_chore': update_chore_tool
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest test_chore_functions.py -v`
Expected: all tests PASS (including pre-existing ones)

- [ ] **Step 5: Commit**

```bash
git add chore_functions.py test_chore_functions.py
git commit -m "$(cat <<'EOF'
Add list_all_chores tool wrapper

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Register the tool schema in `model_config.json`

**Files:**
- Modify: `model_config.json` (add to the `tools` array, after the `list_outstanding_chores` entry currently at lines 47-57)
- Test: `test_model_config.py` (check existing test file for pattern before adding)

**Interfaces:**
- Consumes: nothing new — this is a static schema entry, function name `list_all_chores` must match `TOOL_FUNCTIONS` key from Task 2 exactly.
- Produces: a `tools[]` entry the OpenAI/OpenRouter API uses to decide when to call `list_all_chores`. No parameters beyond none (mirrors `list_outstanding_chores`'s empty `properties: {}` shape).

Note: `test_model_config.py::test_model_config_tools_match_chore_functions` asserts `{tool['function']['name'] for tool in config['tools']} == set(TOOL_FUNCTIONS.keys())` — this is a dynamic set comparison, not a hardcoded count, so it needs no edits. It will fail until this task's schema entry is added (since Task 2 already added `list_all_chores` to `TOOL_FUNCTIONS`), and pass once it is. No test file changes needed in this task.

- [ ] **Step 1: Run the test to see the current mismatch**

Run: `python3 -m pytest test_model_config.py::test_model_config_tools_match_chore_functions -v`
Expected: FAIL — `TOOL_FUNCTIONS` (from Task 2) now has `list_all_chores` but `model_config.json`'s `tools` list doesn't yet.

- [ ] **Step 2: Add the schema entry to `model_config.json`**

Insert after the `list_outstanding_chores` tool entry (currently ending at line 57, right before the `complete_chore` entry starts at line 58):

```json
    {
      "type": "function",
      "function": {
        "name": "list_all_chores",
        "description": "List every chore the user has, regardless of due status, with last-done and next-due dates. Use this when the user asks to see their full chore list, all chores, or what they're tracking overall — not just what's due or overdue.",
        "parameters": {
          "type": "object",
          "properties": {}
        }
      }
    },
```

- [ ] **Step 3: Validate JSON and run tests**

Run: `python3 -c "import json; json.load(open('model_config.json'))" && echo "valid json"`
Expected: `valid json`

Run: `python3 -m pytest test_model_config.py test_setup.py -v`
Expected: all tests PASS, including `test_model_config_tools_match_chore_functions`

- [ ] **Step 4: Commit**

```bash
git add model_config.json
git commit -m "$(cat <<'EOF'
Register list_all_chores tool schema

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Update `system_prompt.md` guidance

**Files:**
- Modify: `system_prompt.md`

**Interfaces:**
- Consumes: the plain-text line format produced by Task 2's `list_all_chores_tool` (`"<name> | status: <status> | last_done: <last_done> | next_due: <next_due>"`), so the LLM knows how to parse and re-voice it.
- Produces: no code interface — this is prompt text guiding the LLM's behavior. No later task depends on exact wording.

- [ ] **Step 1: Add a new primary function line**

In the `## Primary Functions` section (currently lines 20-25), add a new numbered item after item 1 (`list_outstanding_chores`):

```markdown
1. **Check outstanding chores** - call `list_outstanding_chores()` when the user asks what's due, pending, or outstanding
2. **Check the full chore list** - call `list_all_chores()` when the user asks to see everything they're tracking, their full chore list, or "what chores do I have" — not just what's due
3. **Set up a scheduled chore** - call `add_chore()` when the user wants to start tracking a new recurring chore
4. **Log chore completion (with optional remarks)** - call `complete_chore()` when the user says they've done a chore; pass along any remark they mention
5. **Update an existing chore's schedule** - call `update_chore()` when the user wants to change how often a chore repeats or adjust its grace period
```

(This renumbers the existing items 2-4 to 3-5 — replace the whole block.)

- [ ] **Step 2: Add formatting guidance for the new tool's plain-text output**

In `## Function-Calling Guidance` (currently lines 27-32), add a bullet:

```markdown
- `list_all_chores()` returns plain, unformatted lines (`name | status: ... | last_done: ... | next_due: ...`) — you must convert each line into an HTML-formatted, Claptrap-voiced list item yourself. Never relay the raw pipe-delimited text to the user.
```

- [ ] **Step 3: Add an example interaction**

In `## Example Interactions` (currently lines 55-77), add after the "Checking outstanding chores" example:

````markdown
**Checking the full chore list:**
```
User: what chores do I have?
You: 📋 <b>Behold the FULL ledger of your duties, minion!</b>

• <b>Water plants</b> — OVERDUE (last done: 2026-06-28, next due: 2026-07-01)
• <b>Vacuum living room</b> — due (last done: 2026-07-01, next due: 2026-07-08)
• <b>Wash bedsheets</b> — ok (last done: 2026-07-06, next due: 2026-07-20)

Claptrap remembers EVERYTHING. Bow before my magnificent memory banks! 🤖
```
````

- [ ] **Step 4: Verify no test depends on exact system_prompt.md wording**

Run: `grep -rn "system_prompt" test_*.py`
Expected: any matches only check the file exists/loads (e.g. `get_system_prompt()` returning non-empty), not specific wording. If a test does assert specific text you changed, update it to match.

- [ ] **Step 5: Commit**

```bash
git add system_prompt.md
git commit -m "$(cat <<'EOF'
Document list_all_chores in Claptrap's system prompt

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Full regression pass

**Files:** none (verification only)

**Interfaces:** none — this task only runs the existing suite plus manual smoke check.

- [ ] **Step 1: Run the full test suite**

Run: `python3 -m pytest -v`
Expected: all tests PASS, no failures or errors (compare total count against the pre-Task-1 baseline plus the 8 new tests added across Tasks 1-2)

- [ ] **Step 2: Run `test_setup.py` as a smoke check**

Run: `python3 test_setup.py`
Expected: `✅ All 5 tests passed! Bot is ready to run.`

- [ ] **Step 3: Manually verify via Telegram (requires running bot)**

Start the bot (`python bot.py`), then in Telegram send: `what chores do I have?`
Expected: a reply in Claptrap's voice listing every seeded chore with status and next-due date, formatted with HTML tags (no raw pipe-delimited text, no asterisks).

- [ ] **Step 4: Push**

```bash
git push origin main
```
