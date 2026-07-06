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


def test_complete_chore_tool_includes_remark():
    chore_functions.TOOL_FUNCTIONS['add_chore'](user_id="123", name="Water plants", interval_days=3)

    result = chore_functions.TOOL_FUNCTIONS['complete_chore'](user_id="123", name="Water plants", remark="used less water")

    assert "Water plants" in result
    assert "used less water" in result


def test_complete_chore_tool_without_remark_omits_remark_text():
    chore_functions.TOOL_FUNCTIONS['add_chore'](user_id="123", name="Water plants", interval_days=3)

    result = chore_functions.TOOL_FUNCTIONS['complete_chore'](user_id="123", name="Water plants")

    assert "Water plants" in result
    assert "Remark logged" not in result
    assert not result.startswith("❌")


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
