import os
import re
import json
from datetime import datetime, timedelta

CHORES_DIR = "chores"
NOTIFICATION_STATE_FILE = os.path.join(CHORES_DIR, ".notification_state.json")


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


def get_last_notification_run() -> str:
    """Returns the ISO date (UTC) the daily notification job last completed, or None."""
    if not os.path.exists(NOTIFICATION_STATE_FILE):
        return None
    try:
        with open(NOTIFICATION_STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f).get("last_run_date")
    except (json.JSONDecodeError, OSError):
        return None


def set_last_notification_run(iso_date: str) -> None:
    _ensure_chores_dir()
    with open(NOTIFICATION_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump({"last_run_date": iso_date}, f)


def list_all_user_ids() -> list:
    _ensure_chores_dir()
    user_ids = []
    for filename in os.listdir(CHORES_DIR):
        if filename.startswith("chore_") and filename.endswith(".json"):
            user_ids.append(filename[len("chore_"):-len(".json")])
    return user_ids
