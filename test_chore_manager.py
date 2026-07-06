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
