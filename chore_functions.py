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

    lines = ["📋 <b>Outstanding chores, minion:</b>"]
    for chore in outstanding:
        status_label = "OVERDUE" if chore["status"] == "overdue" else "due"
        lines.append(f"• <b>{chore['name']}</b> — {status_label} (last done: {chore['last_done']})")
    return "\n".join(lines)


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
    'list_all_chores': list_all_chores_tool,
    'complete_chore': complete_chore_tool,
    'update_chore': update_chore_tool
}
