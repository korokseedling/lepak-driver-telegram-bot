import chore_manager
import response_templates as templates


def add_chore_tool(user_id, name, interval_days, grace_days=3):
    try:
        chore = chore_manager.add_chore(user_id, name, interval_days, grace_days)
    except ValueError as e:
        return templates.render_error(str(e))
    return templates.render_add_chore(chore['name'], chore['interval_days'], chore['grace_days'])


def list_outstanding_chores_tool(user_id):
    outstanding = chore_manager.list_outstanding(user_id)
    if not outstanding:
        return templates.render_outstanding_empty()

    lines = [templates.render_outstanding_header()]
    for chore in outstanding:
        status_label = "OVERDUE" if chore["status"] == "overdue" else "due"
        lines.append(f"• <b>{chore['name']}</b> — {status_label} (last done: {templates.format_friendly_date(chore['last_done'])})")
    return "\n".join(lines)


def list_all_chores_tool(user_id):
    all_chores = chore_manager.list_all(user_id)
    if not all_chores:
        return templates.render_all_empty()

    lines = [templates.render_all_header()]
    for chore in all_chores:
        status_label = "OVERDUE" if chore["status"] == "overdue" else chore["status"]
        lines.append(
            f"• <b>{chore['name']}</b> — {status_label} "
            f"(last done: {templates.format_friendly_date(chore['last_done'])}, "
            f"next due: {templates.format_friendly_date(chore['next_due'])})"
        )
    return "\n".join(lines)


def complete_chore_tool(user_id, name, remark=None):
    try:
        chore = chore_manager.complete_chore(user_id, name, remark)
    except ValueError as e:
        return templates.render_error(str(e))
    return templates.render_complete_chore(chore['name'], remark)


def update_chore_tool(user_id, name, interval_days=None, grace_days=None):
    try:
        chore = chore_manager.update_chore(user_id, name, interval_days, grace_days)
    except ValueError as e:
        return templates.render_error(str(e))
    return templates.render_update_chore(chore['name'], chore['interval_days'], chore['grace_days'])


def format_daily_notification(user_id):
    data = chore_manager.load_chores(user_id)
    due = []
    overdue = []
    for chore in data["chores"]:
        status = chore_manager.get_chore_status(chore)
        if status == "due":
            due.append(chore)
        elif status == "overdue":
            overdue.append(chore)

    if not due and not overdue:
        return None

    lines = []
    if overdue:
        lines.append("🚨 <b>ATTENTION, MINION!</b> Claptrap has detected NEGLECTED CHORES:")
        for chore in overdue:
            lines.append(f"• <b>{chore['name']}</b> — overdue (last done: {templates.format_friendly_date(chore['last_done'])})")
    if due:
        lines.append("📋 <b>Heads up, minion!</b> These have just come due:")
        for chore in due:
            lines.append(f"• <b>{chore['name']}</b> — due (last done: {templates.format_friendly_date(chore['last_done'])})")
    if overdue:
        lines.append("Fix this immediately, or face... mild disappointment from a very important robot.")
    return "\n".join(lines)


TOOL_FUNCTIONS = {
    'add_chore': add_chore_tool,
    'list_outstanding_chores': list_outstanding_chores_tool,
    'list_all_chores': list_all_chores_tool,
    'complete_chore': complete_chore_tool,
    'update_chore': update_chore_tool
}
