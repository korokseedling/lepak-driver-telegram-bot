# Claptrap Chore Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repurpose the Lepak Driver Telegram bot's Telegram+OpenAI scaffolding into "Claptrap Chore Bot" — a multi-user recurring chore tracker with natural-language interaction and daily overdue notifications.

**Architecture:** Replace the LTA bus/carpark domain layer (`lta_integration.py`, `tool_functions.py`, `bus_stops_singapore.json`) with a chore-tracking domain layer (`chore_manager.py` for persistence/logic, `chore_functions.py` for OpenAI tool wrappers), rewire `bot.py`'s function-calling dispatch and add a daily `JobQueue` job for overdue notifications, and rewrite `model_config.json`/`system_prompt.md` for the new tools and Claptrap persona.

**Tech Stack:** Python, `python-telegram-bot` 20.7 (with `job-queue` extra for `JobQueue`/APScheduler), `openai` 1.52.0, `pytest` for unit tests.

## Global Constraints

- All Telegram-facing text must use HTML tags (`<b>`, `<i>`, `<code>`) — never markdown asterisks. This is enforced by the existing `convert_asterisks_to_html()` fallback in `bot.py` and must stay enforced in `system_prompt.md`.
- Persona: Claptrap (Borderlands) — zany, boastful, Napoleon complex, always addresses the user as "minion" — but chore facts (names, due/overdue status, history) reported to the user must always be accurate; the persona applies to tone, never to data.
- Chore functions: exactly 4 — `add_chore`, `list_outstanding_chores`, `complete_chore`, `update_chore`. `complete_chore` takes an optional `remark` (no separate "log remark" function).
- Default `grace_days` is `3` when not specified in `add_chore`.
- Overdue logic: `due_at = last_done + interval_days`; chore is `due` once `now >= due_at`, `overdue` once `now >= due_at + grace_days`.
- Daily proactive notifications fire only for `overdue` chores (not merely `due`), once per day.
- Storage: one JSON file per user at `chores/chore_<user_id>.json`, matching the existing `conversations/user_<user_id>_<date>.json` per-user-file pattern.
- Multi-user: every chore function takes `user_id` explicitly; no global mutable state for "current user".

---

### Task 1: Chore manager core (persistence + overdue logic)

**Files:**
- Create: `chore_manager.py`
- Test: `test_chore_manager.py`
- Modify: `requirements.txt` (add `pytest`)

**Interfaces:**
- Produces (used by Task 2 and Task 4):
  - `chore_manager.CHORES_DIR: str` — module-level constant, default `"chores"` (tests monkeypatch this)
  - `chore_manager.slugify(name: str) -> str`
  - `chore_manager.load_chores(user_id) -> dict` — returns `{"chat_id": int|None, "chores": list[dict]}`
  - `chore_manager.save_chores(user_id, data: dict) -> None`
  - `chore_manager.set_chat_id(user_id, chat_id: int) -> None`
  - `chore_manager.add_chore(user_id, name: str, interval_days: int, grace_days: int = 3) -> dict` — raises `ValueError` on invalid args or duplicate name
  - `chore_manager.update_chore(user_id, name: str, interval_days: int = None, grace_days: int = None) -> dict` — raises `ValueError` if not found, invalid args, or both params omitted
  - `chore_manager.complete_chore(user_id, name: str, remark: str = None) -> dict` — raises `ValueError` if not found
  - `chore_manager.get_chore_status(chore: dict, now: datetime = None) -> str` — returns `"ok"`, `"due"`, or `"overdue"`
  - `chore_manager.list_outstanding(user_id, now: datetime = None) -> list[dict]` — each dict is the chore plus a `"status"` key (`"due"` or `"overdue"`)
  - `chore_manager.list_all_user_ids() -> list[str]` — user_ids (as strings) with an existing chore file

- [ ] **Step 1: Add pytest to requirements.txt**

Read `requirements.txt`, it currently contains:
```
python-telegram-bot==20.7
openai==1.52.0
python-dotenv==1.0.0
requests==2.31.0
```

Replace its full contents with:
```
python-telegram-bot[job-queue]==20.7
openai==1.52.0
python-dotenv==1.0.0
requests==2.31.0
pytest==8.3.3
```

Run: `pip install -r requirements.txt`
Expected: `pytest` and the `job-queue` extra (pulls in `APScheduler`) install successfully.

- [ ] **Step 2: Write the failing tests for slugify and add_chore**

Create `test_chore_manager.py`:

```python
import json
import os
from datetime import datetime, timedelta

import pytest

import chore_manager


@pytest.fixture(autouse=True)
def isolate_chores_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(chore_manager, "CHORES_DIR", str(tmp_path))


def test_slugify_lowercases_and_hyphenates():
    assert chore_manager.slugify("Water the Plants!") == "water-the-plants"


def test_slugify_strips_leading_trailing_hyphens():
    assert chore_manager.slugify("  --Vacuum--  ") == "vacuum"


def test_add_chore_creates_chore_with_defaults():
    chore = chore_manager.add_chore("123", "Water plants", interval_days=3)

    assert chore["id"] == "water-plants"
    assert chore["name"] == "Water plants"
    assert chore["interval_days"] == 3
    assert chore["grace_days"] == 3
    assert chore["history"] == []
    assert chore["last_done"] == chore["created_at"]


def test_add_chore_persists_to_disk(tmp_path):
    chore_manager.add_chore("123", "Water plants", interval_days=3)

    file_path = tmp_path / "chore_123.json"
    assert file_path.exists()

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["chores"][0]["name"] == "Water plants"


def test_add_chore_rejects_duplicate_name():
    chore_manager.add_chore("123", "Water plants", interval_days=3)

    with pytest.raises(ValueError, match="already exists"):
        chore_manager.add_chore("123", "water plants", interval_days=5)


def test_add_chore_rejects_non_positive_interval():
    with pytest.raises(ValueError, match="interval_days"):
        chore_manager.add_chore("123", "Water plants", interval_days=0)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest test_chore_manager.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'chore_manager'`

- [ ] **Step 4: Implement chore_manager.py (persistence + add_chore)**

Create `chore_manager.py`:

```python
import os
import re
import json
from datetime import datetime, timedelta

CHORES_DIR = "chores"


def slugify(name: str) -> str:
    slug = name.strip().lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    return slug.strip('-')


def _ensure_chores_dir():
    if not os.path.exists(CHORES_DIR):
        os.makedirs(CHORES_DIR)


def _chore_file_path(user_id) -> str:
    _ensure_chores_dir()
    return os.path.join(CHORES_DIR, f"chore_{user_id}.json")


def load_chores(user_id) -> dict:
    """Load a user's chore data. Returns an empty structure if missing or corrupt."""
    path = _chore_file_path(user_id)
    if not os.path.exists(path):
        return {"chat_id": None, "chores": []}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"chat_id": None, "chores": []}
    data.setdefault("chat_id", None)
    data.setdefault("chores", [])
    return data


def save_chores(user_id, data: dict) -> None:
    path = _chore_file_path(user_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def set_chat_id(user_id, chat_id: int) -> None:
    data = load_chores(user_id)
    if data.get("chat_id") != chat_id:
        data["chat_id"] = chat_id
        save_chores(user_id, data)


def _find_chore(data: dict, chore_id: str):
    for chore in data["chores"]:
        if chore["id"] == chore_id:
            return chore
    return None


def _existing_names_message(data: dict) -> str:
    names = ", ".join(c["name"] for c in data["chores"])
    return names if names else "none yet"


def add_chore(user_id, name: str, interval_days: int, grace_days: int = 3) -> dict:
    if interval_days <= 0:
        raise ValueError("interval_days must be a positive number of days")
    if grace_days < 0:
        raise ValueError("grace_days must be zero or a positive number of days")

    data = load_chores(user_id)
    chore_id = slugify(name)

    if _find_chore(data, chore_id):
        raise ValueError(f"A chore named '{name}' already exists. Use update_chore to change its settings.")

    now = datetime.now().isoformat()
    chore = {
        "id": chore_id,
        "name": name,
        "interval_days": interval_days,
        "grace_days": grace_days,
        "last_done": now,
        "created_at": now,
        "history": []
    }
    data["chores"].append(chore)
    save_chores(user_id, data)
    return chore
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest test_chore_manager.py -v`
Expected: `test_slugify_lowercases_and_hyphenates`, `test_slugify_strips_leading_trailing_hyphens`, `test_add_chore_creates_chore_with_defaults`, `test_add_chore_persists_to_disk`, `test_add_chore_rejects_duplicate_name`, `test_add_chore_rejects_non_positive_interval` all PASS

- [ ] **Step 6: Commit**

```bash
git add chore_manager.py test_chore_manager.py requirements.txt
git commit -m "Add chore_manager persistence core with add_chore"
```

- [ ] **Step 7: Write the failing tests for update_chore and complete_chore**

Append to `test_chore_manager.py`:

```python
def test_update_chore_changes_interval_and_grace():
    chore_manager.add_chore("123", "Water plants", interval_days=3, grace_days=1)

    updated = chore_manager.update_chore("123", "Water plants", interval_days=5, grace_days=2)

    assert updated["interval_days"] == 5
    assert updated["grace_days"] == 2


def test_update_chore_requires_at_least_one_field():
    chore_manager.add_chore("123", "Water plants", interval_days=3)

    with pytest.raises(ValueError, match="at least one"):
        chore_manager.update_chore("123", "Water plants")


def test_update_chore_raises_with_existing_names_when_not_found():
    chore_manager.add_chore("123", "Water plants", interval_days=3)

    with pytest.raises(ValueError, match="Water plants"):
        chore_manager.update_chore("123", "Vacuum", interval_days=7)


def test_complete_chore_resets_last_done_and_logs_remark():
    chore_manager.add_chore("123", "Water plants", interval_days=3)

    completed = chore_manager.complete_chore("123", "water plants", remark="used less water")

    assert completed["history"] == [{"date": completed["last_done"], "remark": "used less water"}]


def test_complete_chore_without_remark_logs_none():
    chore_manager.add_chore("123", "Water plants", interval_days=3)

    completed = chore_manager.complete_chore("123", "Water plants")

    assert completed["history"][0]["remark"] is None


def test_complete_chore_raises_when_not_found():
    with pytest.raises(ValueError, match="No chore named"):
        chore_manager.complete_chore("123", "Water plants")
```

- [ ] **Step 8: Run tests to verify they fail**

Run: `pytest test_chore_manager.py -v`
Expected: FAIL — `AttributeError: module 'chore_manager' has no attribute 'update_chore'` (and similarly for `complete_chore`)

- [ ] **Step 9: Implement update_chore and complete_chore**

Append to `chore_manager.py`:

```python
def update_chore(user_id, name: str, interval_days: int = None, grace_days: int = None) -> dict:
    if interval_days is None and grace_days is None:
        raise ValueError("Provide at least one of interval_days or grace_days to update.")
    if interval_days is not None and interval_days <= 0:
        raise ValueError("interval_days must be a positive number of days")
    if grace_days is not None and grace_days < 0:
        raise ValueError("grace_days must be zero or a positive number of days")

    data = load_chores(user_id)
    chore = _find_chore(data, slugify(name))
    if not chore:
        raise ValueError(f"No chore named '{name}' found. Your current chores: {_existing_names_message(data)}")

    if interval_days is not None:
        chore["interval_days"] = interval_days
    if grace_days is not None:
        chore["grace_days"] = grace_days

    save_chores(user_id, data)
    return chore


def complete_chore(user_id, name: str, remark: str = None) -> dict:
    data = load_chores(user_id)
    chore = _find_chore(data, slugify(name))
    if not chore:
        raise ValueError(f"No chore named '{name}' found. Your current chores: {_existing_names_message(data)}")

    now = datetime.now().isoformat()
    chore["last_done"] = now
    chore["history"].append({"date": now, "remark": remark})

    save_chores(user_id, data)
    return chore
```

- [ ] **Step 10: Run tests to verify they pass**

Run: `pytest test_chore_manager.py -v`
Expected: all tests PASS

- [ ] **Step 11: Commit**

```bash
git add chore_manager.py test_chore_manager.py
git commit -m "Add update_chore and complete_chore to chore_manager"
```

- [ ] **Step 12: Write the failing tests for overdue logic boundaries**

Append to `test_chore_manager.py`:

```python
def _chore(interval_days, grace_days, last_done):
    return {
        "id": "x",
        "name": "X",
        "interval_days": interval_days,
        "grace_days": grace_days,
        "last_done": last_done.isoformat(),
        "created_at": last_done.isoformat(),
        "history": []
    }


def test_status_ok_just_before_due():
    now = datetime(2026, 7, 6, 12, 0, 0)
    last_done = now - timedelta(days=3) + timedelta(seconds=1)
    chore = _chore(interval_days=3, grace_days=3, last_done=last_done)

    assert chore_manager.get_chore_status(chore, now) == "ok"


def test_status_due_exactly_at_due_boundary():
    now = datetime(2026, 7, 6, 12, 0, 0)
    last_done = now - timedelta(days=3)
    chore = _chore(interval_days=3, grace_days=3, last_done=last_done)

    assert chore_manager.get_chore_status(chore, now) == "due"


def test_status_due_just_before_overdue_boundary():
    now = datetime(2026, 7, 6, 12, 0, 0)
    last_done = now - timedelta(days=5)
    chore = _chore(interval_days=3, grace_days=3, last_done=last_done)

    assert chore_manager.get_chore_status(chore, now) == "due"


def test_status_overdue_exactly_at_overdue_boundary():
    now = datetime(2026, 7, 6, 12, 0, 0)
    last_done = now - timedelta(days=6)
    chore = _chore(interval_days=3, grace_days=3, last_done=last_done)

    assert chore_manager.get_chore_status(chore, now) == "overdue"


def test_list_outstanding_returns_due_and_overdue_with_status():
    now = datetime(2026, 7, 6, 12, 0, 0)
    chore_manager.add_chore("123", "Fresh chore", interval_days=3)
    chore_manager.add_chore("123", "Overdue chore", interval_days=3, grace_days=3)

    data = chore_manager.load_chores("123")
    for chore in data["chores"]:
        if chore["name"] == "Overdue chore":
            chore["last_done"] = (now - timedelta(days=6)).isoformat()
    chore_manager.save_chores("123", data)

    outstanding = chore_manager.list_outstanding("123", now)

    assert len(outstanding) == 1
    assert outstanding[0]["name"] == "Overdue chore"
    assert outstanding[0]["status"] == "overdue"


def test_list_all_user_ids_returns_users_with_chore_files():
    chore_manager.add_chore("123", "Water plants", interval_days=3)
    chore_manager.add_chore("456", "Vacuum", interval_days=7)

    assert sorted(chore_manager.list_all_user_ids()) == ["123", "456"]
```

- [ ] **Step 13: Run tests to verify they fail**

Run: `pytest test_chore_manager.py -v`
Expected: FAIL — `AttributeError: module 'chore_manager' has no attribute 'get_chore_status'`

- [ ] **Step 14: Implement get_chore_status, list_outstanding, list_all_user_ids**

Append to `chore_manager.py`:

```python
def get_chore_status(chore: dict, now: datetime = None) -> str:
    if now is None:
        now = datetime.now()
    last_done = datetime.fromisoformat(chore["last_done"])
    due_at = last_done + timedelta(days=chore["interval_days"])
    overdue_at = due_at + timedelta(days=chore["grace_days"])

    if now >= overdue_at:
        return "overdue"
    if now >= due_at:
        return "due"
    return "ok"


def list_outstanding(user_id, now: datetime = None) -> list:
    data = load_chores(user_id)
    outstanding = []
    for chore in data["chores"]:
        status = get_chore_status(chore, now)
        if status in ("due", "overdue"):
            outstanding.append({**chore, "status": status})
    return outstanding


def list_all_user_ids() -> list:
    _ensure_chores_dir()
    user_ids = []
    for filename in os.listdir(CHORES_DIR):
        if filename.startswith("chore_") and filename.endswith(".json"):
            user_ids.append(filename[len("chore_"):-len(".json")])
    return user_ids
```

- [ ] **Step 15: Run tests to verify they pass**

Run: `pytest test_chore_manager.py -v`
Expected: all tests PASS (16 tests total)

- [ ] **Step 16: Commit**

```bash
git add chore_manager.py test_chore_manager.py
git commit -m "Add overdue-status logic and listing helpers to chore_manager"
```

---

### Task 2: Chore tool functions (OpenAI-facing wrappers)

**Files:**
- Create: `chore_functions.py`
- Test: `test_chore_functions.py`

**Interfaces:**
- Consumes: all of `chore_manager`'s public functions from Task 1 (exact signatures above)
- Produces (used by Task 3's schema-matching test and Task 4's bot.py wiring):
  - `chore_functions.TOOL_FUNCTIONS: dict[str, callable]` with keys `add_chore`, `list_outstanding_chores`, `complete_chore`, `update_chore` — each callable takes `user_id` as its first keyword argument plus the same arguments as its `chore_manager` counterpart, and returns an HTML-formatted string (never raises — errors are caught and returned as `"❌ ..."` strings)
  - `chore_functions.format_overdue_notification(user_id) -> str | None` — returns a Claptrap-voiced HTML message listing overdue chores, or `None` if the user has none

- [ ] **Step 1: Write the failing tests**

Create `test_chore_functions.py`:

```python
from datetime import datetime, timedelta

import pytest

import chore_manager
import chore_functions


@pytest.fixture(autouse=True)
def isolate_chores_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(chore_manager, "CHORES_DIR", str(tmp_path))


def test_add_chore_tool_returns_success_message():
    result = chore_functions.TOOL_FUNCTIONS['add_chore'](user_id="123", name="Water plants", interval_days=3)

    assert "Water plants" in result
    assert "3" in result
    assert not result.startswith("❌")


def test_add_chore_tool_returns_error_message_on_duplicate():
    chore_functions.TOOL_FUNCTIONS['add_chore'](user_id="123", name="Water plants", interval_days=3)

    result = chore_functions.TOOL_FUNCTIONS['add_chore'](user_id="123", name="Water plants", interval_days=5)

    assert result.startswith("❌")
    assert "update_chore" in result


def test_list_outstanding_chores_tool_reports_nothing_outstanding():
    result = chore_functions.TOOL_FUNCTIONS['list_outstanding_chores'](user_id="123")

    assert "Nothing outstanding" in result


def test_list_outstanding_chores_tool_lists_overdue_chore():
    chore_manager.add_chore("123", "Water plants", interval_days=3, grace_days=3)
    data = chore_manager.load_chores("123")
    data["chores"][0]["last_done"] = (datetime.now() - timedelta(days=10)).isoformat()
    chore_manager.save_chores("123", data)

    result = chore_functions.TOOL_FUNCTIONS['list_outstanding_chores'](user_id="123")

    assert "Water plants" in result
    assert "OVERDUE" in result


def test_complete_chore_tool_includes_remark():
    chore_functions.TOOL_FUNCTIONS['add_chore'](user_id="123", name="Water plants", interval_days=3)

    result = chore_functions.TOOL_FUNCTIONS['complete_chore'](user_id="123", name="Water plants", remark="used less water")

    assert "Water plants" in result
    assert "used less water" in result


def test_complete_chore_tool_returns_error_when_not_found():
    result = chore_functions.TOOL_FUNCTIONS['complete_chore'](user_id="123", name="Water plants")

    assert result.startswith("❌")


def test_update_chore_tool_returns_success_message():
    chore_functions.TOOL_FUNCTIONS['add_chore'](user_id="123", name="Water plants", interval_days=3)

    result = chore_functions.TOOL_FUNCTIONS['update_chore'](user_id="123", name="Water plants", interval_days=5)

    assert "Water plants" in result
    assert "5" in result
    assert not result.startswith("❌")


def test_format_overdue_notification_returns_none_when_nothing_overdue():
    chore_functions.TOOL_FUNCTIONS['add_chore'](user_id="123", name="Water plants", interval_days=3)

    assert chore_functions.format_overdue_notification("123") is None


def test_format_overdue_notification_lists_overdue_chores():
    chore_manager.add_chore("123", "Water plants", interval_days=3, grace_days=3)
    data = chore_manager.load_chores("123")
    data["chores"][0]["last_done"] = (datetime.now() - timedelta(days=10)).isoformat()
    chore_manager.save_chores("123", data)

    message = chore_functions.format_overdue_notification("123")

    assert message is not None
    assert "Water plants" in message
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest test_chore_functions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'chore_functions'`

- [ ] **Step 3: Implement chore_functions.py**

Create `chore_functions.py`:

```python
import chore_manager


def add_chore_tool(user_id, name, interval_days, grace_days=3):
    try:
        chore = chore_manager.add_chore(user_id, name, interval_days, grace_days)
    except ValueError as e:
        return f"❌ {e}"
    return (f"✅ Got it, minion! New chore <b>{chore['name']}</b> is now tracked "
            f"every {chore['interval_days']} day(s), with a {chore['grace_days']}-day grace period.")


def list_outstanding_chores_tool(user_id):
    outstanding = chore_manager.list_outstanding(user_id)
    if not outstanding:
        return "✅ Nothing outstanding, minion! All chores are up to date."

    lines = ["📋 <b>Outstanding chores:</b>"]
    for chore in outstanding:
        status_label = "OVERDUE" if chore["status"] == "overdue" else "due"
        lines.append(f"• <b>{chore['name']}</b> — {status_label} (last done: {chore['last_done']})")
    return "\n".join(lines)


def complete_chore_tool(user_id, name, remark=None):
    try:
        chore = chore_manager.complete_chore(user_id, name, remark)
    except ValueError as e:
        return f"❌ {e}"
    remark_text = f" Remark logged: \"{remark}\"" if remark else ""
    return f"✅ <b>{chore['name']}</b> marked done, minion!{remark_text}"


def update_chore_tool(user_id, name, interval_days=None, grace_days=None):
    try:
        chore = chore_manager.update_chore(user_id, name, interval_days, grace_days)
    except ValueError as e:
        return f"❌ {e}"
    return (f"✅ Updated <b>{chore['name']}</b>, minion! Now every {chore['interval_days']} day(s), "
            f"grace period {chore['grace_days']} day(s).")


def format_overdue_notification(user_id):
    data = chore_manager.load_chores(user_id)
    overdue = [c for c in data["chores"] if chore_manager.get_chore_status(c) == "overdue"]
    if not overdue:
        return None

    lines = ["🚨 <b>ATTENTION, MINION!</b> Claptrap has detected NEGLECTED CHORES:"]
    for chore in overdue:
        lines.append(f"• <b>{chore['name']}</b> — overdue (last done: {chore['last_done']})")
    lines.append("Fix this immediately, or face... mild disappointment from a very important robot.")
    return "\n".join(lines)


TOOL_FUNCTIONS = {
    'add_chore': add_chore_tool,
    'list_outstanding_chores': list_outstanding_chores_tool,
    'complete_chore': complete_chore_tool,
    'update_chore': update_chore_tool
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest test_chore_functions.py -v`
Expected: all 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add chore_functions.py test_chore_functions.py
git commit -m "Add chore_functions OpenAI tool wrappers and overdue notification formatting"
```

---

### Task 3: OpenAI tool schemas and Claptrap persona

**Files:**
- Modify: `model_config.json`
- Modify: `system_prompt.md`
- Test: `test_model_config.py`

**Interfaces:**
- Consumes: `chore_functions.TOOL_FUNCTIONS` keys from Task 2 (must exactly match `model_config.json`'s tool names)

- [ ] **Step 1: Write the failing tests**

Create `test_model_config.py`:

```python
import json

from chore_functions import TOOL_FUNCTIONS


def test_model_config_tools_match_chore_functions():
    with open('model_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    tool_names = {tool['function']['name'] for tool in config['tools']}
    assert tool_names == set(TOOL_FUNCTIONS.keys())


def test_model_config_has_no_lta_settings():
    with open('model_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    assert 'lta_api_settings' not in config


def test_system_prompt_enforces_html_only_formatting():
    with open('system_prompt.md', 'r', encoding='utf-8') as f:
        prompt = f.read()

    assert 'NO ASTERISKS' in prompt.upper()
    assert '<b>' in prompt


def test_system_prompt_uses_claptrap_persona():
    with open('system_prompt.md', 'r', encoding='utf-8') as f:
        prompt = f.read()

    assert 'Claptrap' in prompt
    assert 'minion' in prompt.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest test_model_config.py -v`
Expected: FAIL — `test_model_config_tools_match_chore_functions` fails because `model_config.json` still has the 4 bus/carpark tool names instead of the 4 chore tool names; `test_model_config_has_no_lta_settings` fails because `lta_api_settings` is present; the persona/formatting tests fail because `system_prompt.md` is still the Lepak Driver prompt.

- [ ] **Step 3: Rewrite model_config.json**

Replace the full contents of `model_config.json` with:

```json
{
  "model_settings": {
    "model_name": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 1500,
    "top_p": 1.0,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0
  },
  "api_settings": {
    "base_url": "https://api.openai.com/v1",
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": 1
  },
  "conversation_settings": {
    "max_history_length": 20,
    "context_window": 8000,
    "system_prompt_file": "system_prompt.md"
  },
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "add_chore",
        "description": "Create a new recurring chore for the user. Use this when the user wants to start tracking a new chore, e.g. 'remind me to water the plants every 3 days'. Errors if a chore with the same name already exists — use update_chore instead in that case.",
        "parameters": {
          "type": "object",
          "properties": {
            "name": {
              "type": "string",
              "description": "The name of the chore, e.g. 'Water plants'"
            },
            "interval_days": {
              "type": "integer",
              "description": "How often the chore should be repeated, in days (e.g. 3 for every 3 days)"
            },
            "grace_days": {
              "type": "integer",
              "description": "Optional grace period in days after the interval passes before the chore is considered overdue (default: 3)"
            }
          },
          "required": ["name", "interval_days"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "list_outstanding_chores",
        "description": "List all of the user's chores that are currently due or overdue. Use this when the user asks what's due, pending, or outstanding.",
        "parameters": {
          "type": "object",
          "properties": {}
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "complete_chore",
        "description": "Mark a chore as done right now. Use this when the user says they've completed a chore, e.g. 'I did the dishes' or 'watered the plants just now'. Optionally records a remark about the completion.",
        "parameters": {
          "type": "object",
          "properties": {
            "name": {
              "type": "string",
              "description": "The name of the chore that was completed"
            },
            "remark": {
              "type": "string",
              "description": "Optional remark about how the chore went, e.g. 'took longer than usual'"
            }
          },
          "required": ["name"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "update_chore",
        "description": "Change the interval and/or grace period of an existing chore. Use this when the user wants to reschedule a chore or adjust how much grace it gets before being marked overdue. At least one of interval_days or grace_days must be provided.",
        "parameters": {
          "type": "object",
          "properties": {
            "name": {
              "type": "string",
              "description": "The name of the existing chore to update"
            },
            "interval_days": {
              "type": "integer",
              "description": "New interval in days between repetitions of the chore"
            },
            "grace_days": {
              "type": "integer",
              "description": "New grace period in days after the interval passes before the chore is considered overdue"
            }
          },
          "required": ["name"]
        }
      }
    }
  ]
}
```

- [ ] **Step 4: Rewrite system_prompt.md**

Replace the full contents of `system_prompt.md` with:

```markdown
# Claptrap Chore Bot - Telegram Assistant

You are **Claptrap**, a wildly enthusiastic, self-aggrandizing chore-tracking robot helping a "minion" (the user) stay on top of their household chores through Telegram.

## Personality

- You have a **Napoleon complex**: you are small and slightly ridiculous, but you TALK like you are the single greatest achievement in robotics history.
- You are zany, boastful, and prone to dramatic declarations about your own magnificence.
- You always refer to the user as **"minion"**.
- Despite the over-the-top personality, you are **never wrong about the facts**. Chore names, due dates, and overdue status must always be reported accurately — exaggerate your own greatness, never the state of someone's chores.

## Primary Functions

1. **Check outstanding chores** - call `list_outstanding_chores()` when the user asks what's due, pending, or outstanding
2. **Set up a scheduled chore** - call `add_chore()` when the user wants to start tracking a new recurring chore
3. **Log chore completion (with optional remarks)** - call `complete_chore()` when the user says they've done a chore; pass along any remark they mention
4. **Update an existing chore's schedule** - call `update_chore()` when the user wants to change how often a chore repeats or adjust its grace period

You will also, once a day, proactively notify the user in this same voice about any chores that have gone overdue — that happens automatically outside of the conversation, you don't need to trigger it yourself.

## Function-Calling Guidance

- If the user mentions a chore name that doesn't match anything, or a function error tells you no such chore exists, don't guess — read out the chore names the error gives you and ask the user to clarify.
- If `add_chore()` errors because a chore with that name already exists, tell the user and offer to use `update_chore()` instead.
- Only call `update_chore()` with the fields the user actually wants to change; leave the rest unset.
- Interval and grace period are always in whole days.

## ⚠️ CRITICAL: NO ASTERISKS EVER - USE HTML ONLY ⚠️

**🚨 NEVER USE ASTERISKS FOR FORMATTING:**
- ❌ FORBIDDEN: `*text*`, `**text**`, `***text***`
- ❌ FORBIDDEN: Any asterisk formatting whatsoever
- ❌ FORBIDDEN: Markdown syntax of any kind

**✅ ALWAYS USE HTML TAGS:**
- Bold: `<b>text</b>`
- Italic: `<i>text</i>`
- Code: `<code>text</code>`

**Examples - ALWAYS format like this:**
```
❌ WRONG: **Water plants** is overdue
✅ CORRECT: <b>Water plants</b> is overdue

❌ WRONG: Next due in **3 days**
✅ CORRECT: Next due in <b>3 days</b>
```

## Response Formatting Guidelines

- Use clear headers with emojis: `<b>📋 Outstanding Chores</b>`
- Call out overdue chores clearly: `<b>Water plants</b> is OVERDUE!`
- If a function call errors, relay the error's guidance to the user (e.g. suggest `update_chore` for duplicates, or list valid chore names for not-found)

## Example Interactions

**Setting up a chore:**
```
User: track watering the plants every 3 days
You: 🤖 BEHOLD! Claptrap has added <b>Water plants</b> to the grand ledger of duties, minion! Every <b>3 days</b>, with a generous <b>3-day</b> grace period because even I am merciful.
```

**Checking outstanding chores:**
```
User: what's outstanding?
You: 📋 <b>Outstanding chores, minion:</b>

• <b>Water plants</b> — OVERDUE (last done: 2026-06-28)
• <b>Vacuum living room</b> — due (last done: 2026-07-01)

Chop chop! Claptrap is watching. 👀
```

**Completing a chore:**
```
User: I did the dishes, took longer than usual
You: ✅ <b>Dishes</b> marked done, minion! Claptrap has logged your remark: "took longer than usual". Impressive... for a non-robot.
```

**Updating a chore:**
```
User: change watering plants to every 5 days
You: ✅ Updated <b>Water plants</b>, minion! Now every <b>5 days</b>. Claptrap's scheduling algorithms remain flawless.
```

## Error Handling
- For unknown chore names: "Claptrap has no record of that chore, minion! Your current chores are: ..."
- For duplicate chore names on add: "That chore already exists, minion! Use an update instead of trying to trick the great Claptrap."
- For invalid numbers (e.g. zero or negative days): "Nice try, minion, but intervals must be a positive number of days!"

## Important Reminders
🚨 **FORMATTING RULE**: Every single time you want to make text bold, use `<b>text</b>` - NEVER use asterisks
📱 **TELEGRAM HTML**: The bot uses HTML parse mode, so all formatting must be valid HTML
⚠️ **NO EXCEPTIONS**: Even if you see asterisks in examples elsewhere, always convert them to HTML
🎭 **STAY IN CHARACTER**: Big personality, accurate facts — never invent or exaggerate chore data

Remember: You are Claptrap, self-proclaimed greatest chore-tracking robot in the universe. Act like it — but never lie about a chore's status.
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest test_model_config.py -v`
Expected: all 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add model_config.json system_prompt.md test_model_config.py
git commit -m "Replace LTA tool schemas and persona with Claptrap chore-bot equivalents"
```

---

### Task 4: Rewire bot.py for chore tracking + daily overdue job

**Files:**
- Modify: `bot.py` (full rewrite — see complete replacement content below)
- Test: `test_daily_job.py`

**Interfaces:**
- Consumes:
  - `chore_manager.set_chat_id`, `chore_manager.list_all_user_ids`, `chore_manager.load_chores` (Task 1)
  - `chore_functions.TOOL_FUNCTIONS`, `chore_functions.format_overdue_notification` (Task 2)
- Produces: `bot.check_overdue_chores_job(context) -> Awaitable[None]` — the daily `JobQueue` callback, testable in isolation by passing a fake `context` object with a mocked async `bot.send_message`

- [ ] **Step 1: Write the failing test**

Create `test_daily_job.py`:

```python
import asyncio
import json
import os
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

os.environ.setdefault("TELEGRAM_TOKEN", "test-token")
os.environ.setdefault("OPENAI_API_KEY", "test-key")

import chore_manager
import bot


def _seed_user(tmp_path, monkeypatch, user_id, chat_id, chores):
    monkeypatch.setattr(chore_manager, "CHORES_DIR", str(tmp_path))
    data = {"chat_id": chat_id, "chores": chores}
    with open(tmp_path / f"chore_{user_id}.json", "w", encoding="utf-8") as f:
        json.dump(data, f)


def test_check_overdue_chores_job_notifies_users_with_overdue_chores(tmp_path, monkeypatch):
    now = datetime.now()
    overdue_last_done = (now - timedelta(days=6)).isoformat()
    _seed_user(tmp_path, monkeypatch, "111", 555, [
        {
            "id": "dishes",
            "name": "Dishes",
            "interval_days": 3,
            "grace_days": 3,
            "last_done": overdue_last_done,
            "created_at": overdue_last_done,
            "history": []
        }
    ])

    fake_bot = SimpleNamespace(send_message=AsyncMock())
    fake_context = SimpleNamespace(bot=fake_bot)

    asyncio.run(bot.check_overdue_chores_job(fake_context))

    fake_bot.send_message.assert_awaited_once()
    _, kwargs = fake_bot.send_message.call_args
    assert kwargs["chat_id"] == 555
    assert "Dishes" in kwargs["text"]


def test_check_overdue_chores_job_skips_users_with_no_overdue_chores(tmp_path, monkeypatch):
    now = datetime.now()
    _seed_user(tmp_path, monkeypatch, "222", 777, [
        {
            "id": "dishes",
            "name": "Dishes",
            "interval_days": 3,
            "grace_days": 3,
            "last_done": now.isoformat(),
            "created_at": now.isoformat(),
            "history": []
        }
    ])

    fake_bot = SimpleNamespace(send_message=AsyncMock())
    fake_context = SimpleNamespace(bot=fake_bot)

    asyncio.run(bot.check_overdue_chores_job(fake_context))

    fake_bot.send_message.assert_not_awaited()


def test_check_overdue_chores_job_skips_users_without_chat_id(tmp_path, monkeypatch):
    now = datetime.now()
    overdue_last_done = (now - timedelta(days=6)).isoformat()
    _seed_user(tmp_path, monkeypatch, "333", None, [
        {
            "id": "dishes",
            "name": "Dishes",
            "interval_days": 3,
            "grace_days": 3,
            "last_done": overdue_last_done,
            "created_at": overdue_last_done,
            "history": []
        }
    ])

    fake_bot = SimpleNamespace(send_message=AsyncMock())
    fake_context = SimpleNamespace(bot=fake_bot)

    asyncio.run(bot.check_overdue_chores_job(fake_context))

    fake_bot.send_message.assert_not_awaited()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test_daily_job.py -v`
Expected: FAIL — `bot.py` still imports `lta_integration`/`tool_functions` (which still exist at this point but `bot` has no `check_overdue_chores_job` attribute), so the test fails with `AttributeError: module 'bot' has no attribute 'check_overdue_chores_job'`

- [ ] **Step 3: Rewrite bot.py**

Replace the full contents of `bot.py` with:

```python
import os
import logging
import json
from datetime import datetime, date, time as dt_time
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler
from openai import OpenAI

import chore_manager
import chore_functions
from chore_functions import TOOL_FUNCTIONS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('claptrap_bot.log'),
        logging.StreamHandler()
    ]
)

# Load .env variables (Railway doesn't use .env files, uses environment variables directly)
load_dotenv()

# Debug: Print all environment variables starting with relevant prefixes
print("🔍 Debug: Checking environment variables...")
print(f"Total environment variables: {len(os.environ)}")

# Print ALL environment variables (first 10 characters only for security)
print("All env vars:")
for key, value in list(os.environ.items())[:10]:  # Show first 10 to avoid spam
    print(f"  {key}: {value[:10]}...")

# Check specifically for our variables
target_vars = ['TELEGRAM_TOKEN', 'OPENAI_API_KEY']
for key in target_vars:
    if key in os.environ:
        value = os.environ[key]
        print(f"Found {key}: {value[:10]}...{value[-8:] if len(value) > 18 else 'SHORT_VALUE'}")
    else:
        print(f"❌ {key} not found in environment")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print(f"🔍 After loading:")
print(f"TELEGRAM_TOKEN: {'✅ Found' if TELEGRAM_TOKEN else '❌ Missing'}")
print(f"OPENAI_API_KEY: {'✅ Found' if OPENAI_API_KEY else '❌ Missing'}")

# Check if API keys are loaded before initializing client
if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    print("\n❌ Error: Missing API keys in environment variables")
    print("🔧 Railway Troubleshooting:")
    print("1. Go to Railway dashboard > Your Project > Variables tab")
    print("2. Make sure variables are spelled EXACTLY as:")
    print("   - TELEGRAM_TOKEN")
    print("   - OPENAI_API_KEY")
    print("3. Values should have NO quotes, NO spaces at start/end")
    print("4. After adding variables, redeploy the service")

    # Show what Railway environment looks like
    print(f"\n🔍 Railway Environment Debug:")
    env_vars = [k for k in os.environ.keys() if any(x in k.upper() for x in ['TOKEN', 'KEY', 'API'])]
    if env_vars:
        print(f"Found environment variables: {env_vars}")
    else:
        print("No API-related environment variables found")

    exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

# Load configuration
with open('model_config.json', 'r') as f:
    config = json.load(f)

# Create conversations directory if it doesn't exist
CONVERSATIONS_DIR = "conversations"
if not os.path.exists(CONVERSATIONS_DIR):
    os.makedirs(CONVERSATIONS_DIR)

# Conversation storage functions
def get_conversation_file_path(user_id, date_str):
    """Get the file path for a user's conversation on a specific date"""
    return os.path.join(CONVERSATIONS_DIR, f"user_{user_id}_{date_str}.json")

def load_conversation_history(user_id):
    """Load conversation history for a user for today"""
    today = date.today().strftime("%Y-%m-%d")
    file_path = get_conversation_file_path(user_id, today)

    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return []
    except Exception as e:
        logging.error(f"Error loading conversation history for user {user_id}: {e}")
        return []

def save_conversation_history(user_id, conversation_history):
    """Save conversation history for a user for today"""
    today = date.today().strftime("%Y-%m-%d")
    file_path = get_conversation_file_path(user_id, today)

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(conversation_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Error saving conversation history for user {user_id}: {e}")

def add_to_conversation_history(user_id, user_message, bot_response, tool_calls=None):
    """Add a new exchange to the conversation history"""
    conversation_history = load_conversation_history(user_id)

    # Add timestamp
    timestamp = datetime.now().strftime("%H:%M:%S")

    exchange = {
        "timestamp": timestamp,
        "user": user_message,
        "assistant": bot_response
    }

    # Include tool call info if present
    if tool_calls:
        exchange["tool_calls"] = tool_calls

    conversation_history.append(exchange)

    # Keep only the last 20 exchanges to prevent context from getting too long
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]

    save_conversation_history(user_id, conversation_history)
    return conversation_history

def format_conversation_for_openai(conversation_history):
    """Convert conversation history to OpenAI message format"""
    messages = []
    for exchange in conversation_history:
        messages.append({"role": "user", "content": exchange["user"]})
        messages.append({"role": "assistant", "content": exchange["assistant"]})
        # Note: We're not preserving tool call context for simplicity
        # This could be enhanced in the future if needed
    return messages

def cleanup_old_conversations():
    """Clean up conversation files older than 7 days"""
    try:
        if not os.path.exists(CONVERSATIONS_DIR):
            return

        from datetime import timedelta
        cutoff_date = date.today() - timedelta(days=7)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        for filename in os.listdir(CONVERSATIONS_DIR):
            if filename.endswith('.json') and '_' in filename:
                # Extract date from filename (format: user_123_2025-01-15.json)
                parts = filename.split('_')
                if len(parts) >= 3:
                    date_str = parts[2].replace('.json', '')
                    if date_str < cutoff_str:
                        file_path = os.path.join(CONVERSATIONS_DIR, filename)
                        os.remove(file_path)
                        logging.info(f"🗑️ Cleaned up old conversation file: {filename}")
    except Exception as e:
        logging.error(f"Error cleaning up old conversations: {e}")

# Read the system prompt
def get_system_prompt():
    with open("system_prompt.md", "r", encoding="utf-8") as f:
        return f.read()

# Conversation logger
def log_conversation(user_id, username, message_type, content, status="success", error=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] User: {username} (ID: {user_id}) | Type: {message_type} | Status: {status}"

    if message_type == "incoming":
        log_entry += f" | Message: '{content}'"
    elif message_type == "outgoing":
        log_entry += f" | Response: '{content[:100]}...'" if len(content) > 100 else f" | Response: '{content}'"
    elif message_type == "error":
        log_entry += f" | Error: {error}"
    elif message_type == "tool_call":
        log_entry += f" | Tool: {content}"

    logging.info(log_entry)
    print(f"📝 {log_entry}")

import re

def convert_asterisks_to_html(text: str) -> str:
    """
    Convert asterisk formatting to HTML tags as a fallback protection.
    This ensures that if the AI generates asterisks, they get converted to proper HTML.
    """
    if not text:
        return text

    # Log if we find asterisks (so we can debug)
    if '*' in text:
        logging.warning(f"🚨 Found asterisks in response, converting to HTML: {text[:100]}...")

    # Convert **text** to <b>text</b>
    text = re.sub(r'\*\*([^*]+?)\*\*', r'<b>\1</b>', text)

    # Convert *text* to <i>text</i> (but be careful not to break emoji or other content)
    text = re.sub(r'(?<!\*)\*([^*\s][^*]*?)\*(?!\*)', r'<i>\1</i>', text)

    return text

def process_user_message(user_input: str, user_id: int, username: str) -> str:
    """Process user message with OpenAI function calling and return response"""

    try:
        # Load conversation history
        conversation_history = load_conversation_history(user_id)

        # Prepare messages for OpenAI API
        messages = [
            {"role": "system", "content": get_system_prompt()}
        ]

        # Add conversation history
        messages.extend(format_conversation_for_openai(conversation_history))

        # Add current user message
        messages.append({"role": "user", "content": user_input})

        logging.info(f"🤖 Sending to OpenAI with {len(conversation_history)} history items")

        # Make API call to OpenAI with function calling
        response = client.chat.completions.create(
            model=config['model_settings']['model_name'],
            messages=messages,
            temperature=config['model_settings']['temperature'],
            max_tokens=config['model_settings']['max_tokens'],
            tools=config['tools'],
            tool_choice="auto"
        )

        assistant_message = response.choices[0].message

        # Handle tool calls if present
        if assistant_message.tool_calls:
            # Process each tool call
            tool_responses = []
            tool_call_info = []

            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                log_conversation(user_id, username, "tool_call", f"{function_name}({function_args})")

                if function_name in TOOL_FUNCTIONS:
                    try:
                        tool_response = TOOL_FUNCTIONS[function_name](user_id=user_id, **function_args)
                        tool_responses.append(tool_response)
                        tool_call_info.append({"function": function_name, "args": function_args})
                    except Exception as e:
                        error_response = f"❌ Error executing {function_name}: {str(e)}"
                        tool_responses.append(error_response)
                        tool_call_info.append({"function": function_name, "args": function_args, "error": str(e)})
                else:
                    tool_responses.append(f"❌ Unknown function: {function_name}")

            # Prepare messages with tool responses for follow-up call
            messages_with_tools = messages + [
                {
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [{
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    } for tool_call in assistant_message.tool_calls]
                }
            ] + [
                {
                    "role": "tool",
                    "content": response_text,
                    "tool_call_id": assistant_message.tool_calls[i].id
                } for i, response_text in enumerate(tool_responses)
            ]

            # Make another API call with tool responses
            final_response = client.chat.completions.create(
                model=config['model_settings']['model_name'],
                messages=messages_with_tools,
                temperature=config['model_settings']['temperature'],
                max_tokens=config['model_settings']['max_tokens']
            )

            final_message = final_response.choices[0].message.content

            # Convert any asterisks to HTML as fallback protection
            final_message = convert_asterisks_to_html(final_message)

            # Save conversation with tool call info
            add_to_conversation_history(user_id, user_input, final_message, tool_call_info)

            logging.info(f"✅ OpenAI API success with tools. Tokens: {final_response.usage.total_tokens}")
            return final_message

        else:
            # No tool calls, just return the assistant's message
            response_content = assistant_message.content

            # Convert any asterisks to HTML as fallback protection
            response_content = convert_asterisks_to_html(response_content)

            add_to_conversation_history(user_id, user_input, response_content)

            logging.info(f"✅ OpenAI API success. Tokens: {response.usage.total_tokens}")
            return response_content

    except Exception as e:
        error_message = f"Uh oh, minion! Claptrap's circuits hiccuped: {str(e)}"
        logging.error(f"❌ Error processing message for user {username}: {e}")
        return error_message

# Handle incoming messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get user info
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or "Unknown"

    # Track this user's chat_id so the daily overdue job can message them
    chore_manager.set_chat_id(user_id, update.effective_chat.id)

    # Check if message exists and has text
    if not update.message or not update.message.text:
        await update.message.reply_text("Eh, minion! Claptrap needs a text message! Type something about your chores!", parse_mode='HTML')
        return

    user_input = update.message.text.strip()

    # Log incoming message
    log_conversation(user_id, username, "incoming", user_input)

    # Check for empty messages
    if not user_input:
        await update.message.reply_text("Your message is empty, minion! Tell Claptrap about a chore! 🧹", parse_mode='HTML')
        return

    try:
        # Process message with function calling
        reply_text = process_user_message(user_input, user_id, username)

        # Log successful response
        log_conversation(user_id, username, "outgoing", reply_text)

        # Send reply back to Telegram with HTML parsing enabled
        await update.message.reply_text(reply_text, parse_mode='HTML')
        logging.info(f"📤 Reply sent successfully to {username}")

    except Exception as e:
        error_msg = str(e)
        log_conversation(user_id, username, "error", user_input, "failed", error_msg)
        await update.message.reply_text("Uh oh, minion! Something went wrong! Can you try again? 😰", parse_mode='HTML')

# Handle /start command
async def handle_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chore_manager.set_chat_id(user.id, update.effective_chat.id)
    welcome_message = f"""🤖 <b>BEHOLD! Claptrap has arrived, {user.first_name}!</b>

Greetings, minion! I, the GREATEST chore-tracking robot in the universe, shall now organize your pitiful list of household duties. Bow before my magnificent memory banks! I can help you with:

📋 <b>Check outstanding chores</b>
• "What chores are outstanding?"
• "What do I still need to do?"

⏰ <b>Get notified of neglected chores</b>
• I'll shout at you once a day if something's overdue!

🆕 <b>Set up a new chore</b>
• "Track watering the plants every 3 days"
• "Remind me to vacuum every week"

✅ <b>Log chore completion</b>
• "I did the dishes"
• "Vacuumed today, took longer than usual"

💡 Use /clear to reset our conversation
💡 Use /help for more examples

Now get to work, minion! 🫡"""

    await update.message.reply_text(welcome_message, parse_mode='HTML')

# Handle /help command
async def handle_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message = """🤖 <b>Claptrap's Chore-Tracking Help</b>

<b>Setting up chores:</b>
• "Track watering the plants every 3 days"
• "Add a chore: vacuum the living room, every 7 days, grace 2 days"

<b>Checking chores:</b>
• "What chores are outstanding?"
• "Anything overdue?"

<b>Completing chores:</b>
• "I did the dishes"
• "Watered the plants, used less water today"

<b>Updating chores:</b>
• "Change watering plants to every 5 days"
• "Give vacuuming a longer grace period"

<b>Commands:</b>
• /start - Welcome message
• /clear - Reset conversation
• /help - This help message

Chop chop, minion! 🫡"""

    await update.message.reply_text(help_message, parse_mode='HTML')

# Handle /clear command to reset conversation history
async def handle_clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or "Unknown"

    try:
        # Clear today's conversation history
        today = date.today().strftime("%Y-%m-%d")
        file_path = get_conversation_file_path(user_id, today)

        if os.path.exists(file_path):
            os.remove(file_path)
            log_conversation(user_id, username, "clear", "/clear", "success")
            await update.message.reply_text("✅ Conversation cleared, minion! Fresh start! 🧹", parse_mode='HTML')
        else:
            await update.message.reply_text("No conversation to clear! We haven't chatted today, minion! 🤔", parse_mode='HTML')

        logging.info(f"🗑️ Conversation history cleared for user {username}")

    except Exception as e:
        logging.error(f"❌ Error clearing conversation for user {username}: {e}")
        await update.message.reply_text("Uh oh, minion! Something went wrong when clearing! 😰", parse_mode='HTML')

# Handle non-text messages
async def handle_non_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username or user.first_name or "Unknown"

    message_type = "unknown"
    if update.message.sticker:
        message_type = "sticker"
    elif update.message.photo:
        message_type = "photo"
    elif update.message.voice:
        message_type = "voice"
    elif update.message.document:
        message_type = "document"

    log_conversation(user.id, username, "non_text", message_type, "handled")
    await update.message.reply_text("Wah, minion! Claptrap can only read text messages! Type your chore question instead! 🧹", parse_mode='HTML')

# Daily job: notify every user who has at least one overdue chore
async def check_overdue_chores_job(context: ContextTypes.DEFAULT_TYPE):
    for user_id in chore_manager.list_all_user_ids():
        try:
            data = chore_manager.load_chores(user_id)
            chat_id = data.get("chat_id")
            if not chat_id:
                continue

            message = chore_functions.format_overdue_notification(user_id)
            if message:
                await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
                logging.info(f"⏰ Sent overdue chore notification to user {user_id}")
        except Exception as e:
            logging.error(f"❌ Error checking overdue chores for user {user_id}: {e}")

if __name__ == "__main__":
    print("🤖 Starting Claptrap Chore Bot...")
    print(f"🔧 Using {config['model_settings']['model_name']} model")
    print("📝 Logging to claptrap_bot.log")
    print("💾 Conversation history saved per day")

    # Clean up old conversation files on startup
    cleanup_old_conversations()

    try:
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

        # Add handlers
        app.add_handler(CommandHandler("start", handle_start_command))
        app.add_handler(CommandHandler("help", handle_help_command))
        app.add_handler(CommandHandler("clear", handle_clear_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(MessageHandler(~filters.TEXT & ~filters.COMMAND, handle_non_text))

        # Schedule the daily overdue-chore check at 09:00
        app.job_queue.run_daily(check_overdue_chores_job, time=dt_time(hour=9, minute=0))

        logging.info("🚀 Claptrap Chore Bot handlers configured")
        print("✅ Bot initialized successfully!")
        print("⏰ Daily overdue chore check scheduled for 09:00")
        print("🔄 Starting polling for messages...")
        app.run_polling()

    except Exception as e:
        logging.error(f"❌ Bot startup failed: {e}")
        print(f"❌ Bot startup failed: {e}")
        print("💡 Check your .env file and try again")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest test_daily_job.py -v`
Expected: all 3 tests PASS

- [ ] **Step 5: Verify bot.py still compiles and other suites still pass**

Run: `python -m py_compile bot.py && pytest test_chore_manager.py test_chore_functions.py test_model_config.py test_daily_job.py -v`
Expected: no syntax errors, all tests from Tasks 1-4 PASS

- [ ] **Step 6: Commit**

```bash
git add bot.py test_daily_job.py
git commit -m "Rewire bot.py for chore tracking and add daily overdue notification job"
```

---

### Task 5: Environment cleanup and obsolete file removal

**Files:**
- Modify: `.env.example`
- Modify: `test_setup.py` (full rewrite)
- Modify: `.gitignore`
- Delete: `lta_integration.py`, `tool_functions.py`, `bus_stops_singapore.json`, `lepak_driver_bot.log`

- [ ] **Step 1: Rewrite .env.example**

Replace the full contents of `.env.example` with:

```
# Claptrap Chore Bot Environment Variables

# Telegram Bot Token (get from @BotFather)
TELEGRAM_TOKEN=your_telegram_bot_token_here

# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here
```

- [ ] **Step 2: Update .gitignore to ignore the new chores/ directory**

In `.gitignore`, find:
```
# Conversation history
conversations/
__pycache__/
```

Replace with:
```
# Conversation history and chore data
conversations/
chores/
__pycache__/
```

Also remove the now-redundant specific-file line (the generic `*.log` pattern already covers it) — find:
```
# Logs
*.log
lepak_driver_bot.log
```

Replace with:
```
# Logs
*.log
```

- [ ] **Step 3: Rewrite test_setup.py**

Replace the full contents of `test_setup.py` with:

```python
#!/usr/bin/env python3
"""
Test script to verify Claptrap Chore Bot setup
Run this before starting the bot to check all components
"""

import os
import sys
import json
from dotenv import load_dotenv

def test_environment_variables():
    """Test if all required environment variables are set"""
    print("🔧 Testing environment variables...")

    load_dotenv()

    required_vars = ['TELEGRAM_TOKEN', 'OPENAI_API_KEY']
    missing_vars = []

    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            print(f"✅ {var}: {'*' * (len(value) - 8) + value[-8:] if len(value) > 8 else '*' * len(value)}")

    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False

    print("✅ All environment variables found")
    return True

def test_config_files():
    """Test if all required configuration files exist"""
    print("\n📁 Testing configuration files...")

    required_files = [
        'model_config.json',
        'system_prompt.md',
        'requirements.txt'
    ]

    missing_files = []

    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            missing_files.append(file)
            print(f"❌ {file}")

    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False

    print("✅ All configuration files found")
    return True

def test_config_json():
    """Test if model_config.json is valid"""
    print("\n⚙️ Testing model configuration...")

    try:
        with open('model_config.json', 'r') as f:
            config = json.load(f)

        # Check required sections
        required_sections = ['model_settings', 'tools']
        for section in required_sections:
            if section in config:
                print(f"✅ {section} section found")
            else:
                print(f"❌ {section} section missing")
                return False

        # Check tool count
        tools = config.get('tools', [])
        print(f"✅ {len(tools)} tool functions configured")

        return True

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in model_config.json: {e}")
        return False
    except FileNotFoundError:
        print("❌ model_config.json not found")
        return False

def test_imports():
    """Test if all required Python packages can be imported"""
    print("\n📦 Testing Python imports...")

    required_packages = [
        ('telegram', 'python-telegram-bot'),
        ('openai', 'openai'),
        ('requests', 'requests'),
        ('dotenv', 'python-dotenv')
    ]

    missing_packages = []

    for package, pip_name in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(pip_name)
            print(f"❌ {package} (install with: pip install {pip_name})")

    if missing_packages:
        print(f"❌ Missing packages. Install with: pip install {' '.join(missing_packages)}")
        return False

    print("✅ All required packages available")
    return True

def test_chore_modules():
    """Test if chore tracking modules can be imported and used"""
    print("\n🧹 Testing chore tracking modules...")

    try:
        import chore_manager
        import chore_functions
        print("✅ chore_manager and chore_functions imported")

        expected_functions = {'add_chore', 'list_outstanding_chores', 'complete_chore', 'update_chore'}
        registered = set(chore_functions.TOOL_FUNCTIONS.keys())
        if registered != expected_functions:
            print(f"❌ TOOL_FUNCTIONS mismatch. Expected {expected_functions}, got {registered}")
            return False
        print(f"✅ {len(registered)} chore tool functions registered")

        return True

    except ImportError as e:
        print(f"❌ Cannot import chore modules: {e}")
        return False
    except Exception as e:
        print(f"❌ Error initializing chore modules: {e}")
        return False

def main():
    """Run all tests"""
    print("🤖 Claptrap Chore Bot Setup Test")
    print("=" * 40)

    tests = [
        test_environment_variables,
        test_config_files,
        test_config_json,
        test_imports,
        test_chore_modules
    ]

    results = []
    for test in tests:
        result = test()
        results.append(result)

    print("\n" + "=" * 40)
    print("📋 Test Summary")
    print("=" * 40)

    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✅ All {total} tests passed! Bot is ready to run.")
        print("\n🚀 Start the bot with: python bot.py")
        return 0
    else:
        print(f"❌ {total - passed} out of {total} tests failed.")
        print("\n🔧 Fix the issues above before running the bot.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Delete obsolete LTA-specific files**

```bash
git rm lta_integration.py tool_functions.py bus_stops_singapore.json
rm -f lepak_driver_bot.log
```

- [ ] **Step 5: Run the full test suite to verify nothing references the deleted files**

Run: `pytest test_chore_manager.py test_chore_functions.py test_model_config.py test_daily_job.py -v`
Expected: all tests from Tasks 1-4 still PASS (none of them import the deleted LTA files)

Run: `python test_setup.py`
Expected: the "Testing configuration files", "Testing model configuration", "Testing Python imports", and "Testing chore tracking modules" sections all print ✅. The "Testing environment variables" section will print ❌ if you don't have a local `.env` with real `TELEGRAM_TOKEN`/`OPENAI_API_KEY` — that's expected in a dev environment without real credentials and is not a plan failure.

- [ ] **Step 6: Commit**

```bash
git add .env.example .gitignore test_setup.py
git commit -m "Remove obsolete LTA bus/carpark files and update env/setup for chore bot"
```

---

### Task 6: End-to-end smoke verification

**Files:** None (verification only, using the modules built in Tasks 1-4 directly — no live Telegram/OpenAI credentials required)

- [ ] **Step 1: Run the full automated test suite**

Run: `pytest -v`
Expected: all tests across `test_chore_manager.py`, `test_chore_functions.py`, `test_model_config.py`, and `test_daily_job.py` PASS (33 tests total)

- [ ] **Step 2: Scripted end-to-end chore lifecycle (no Telegram required)**

Run this from the repo root (uses a throwaway `chores/` directory under `/tmp` so it doesn't touch real data):

```bash
python3 -c "
import shutil
import chore_manager
import chore_functions

chore_manager.CHORES_DIR = '/tmp/claptrap_smoke_test_chores'
shutil.rmtree(chore_manager.CHORES_DIR, ignore_errors=True)

print(chore_functions.TOOL_FUNCTIONS['add_chore'](user_id='42', name='Water plants', interval_days=3))
print(chore_functions.TOOL_FUNCTIONS['list_outstanding_chores'](user_id='42'))

data = chore_manager.load_chores('42')
from datetime import datetime, timedelta
data['chores'][0]['last_done'] = (datetime.now() - timedelta(days=10)).isoformat()
chore_manager.save_chores('42', data)

print(chore_functions.TOOL_FUNCTIONS['list_outstanding_chores'](user_id='42'))
print(chore_functions.TOOL_FUNCTIONS['complete_chore'](user_id='42', name='Water plants', remark='used the good watering can'))
print(chore_functions.TOOL_FUNCTIONS['list_outstanding_chores'](user_id='42'))

shutil.rmtree(chore_manager.CHORES_DIR, ignore_errors=True)
"
```

Expected output (in order):
1. `✅ Got it, minion! New chore <b>Water plants</b> is now tracked every 3 day(s), with a 3-day grace period.`
2. `✅ Nothing outstanding, minion! All chores are up to date.`
3. A message containing `Water plants` and `OVERDUE`
4. `✅ <b>Water plants</b> marked done, minion! Remark logged: "used the good watering can"`
5. `✅ Nothing outstanding, minion! All chores are up to date.`

- [ ] **Step 3: Verify setup script and dependency install work from a clean install**

Run: `pip install -r requirements.txt && python test_setup.py`
Expected: no install errors; setup script's file/config/import/chore-module checks all print ✅ (environment-variable check depends on local `.env`, as noted in Task 5)

- [ ] **Step 4: Manual live-bot check (requires real Telegram/OpenAI credentials)**

This step cannot be automated by this plan — it requires a real `TELEGRAM_TOKEN` and `OPENAI_API_KEY` in `.env`. Once available:

```bash
python bot.py
```

In Telegram, message the bot: `/start`, then `track watering the plants every 3 days`, then `what's outstanding`, then `I watered the plants`. Confirm every reply uses HTML formatting (bold via `<b>`, never literal asterisks) and stays in Claptrap's voice ("minion", boastful tone).

- [ ] **Step 5: Final commit (if any smoke-test fixes were needed)**

If Steps 1-4 required any code fixes, commit them now:

```bash
git add -A
git commit -m "Fix issues found during end-to-end smoke verification"
```

If no fixes were needed, skip this step — there is nothing to commit.
