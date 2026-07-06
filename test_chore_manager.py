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
