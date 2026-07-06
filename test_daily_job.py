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
