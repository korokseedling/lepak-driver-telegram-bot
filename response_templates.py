import random

_bags = {}


def _draw(key, templates):
    bag = _bags.get(key)
    if not bag:
        bag = templates[:]
        random.shuffle(bag)
        _bags[key] = bag
    return bag.pop()


ADD_CHORE_TEMPLATES = [
    "🤖 SO ORDERED, minion! <b>{name}</b> now joins the grand ledger of duties I ALONE maintain — every {interval} day(s), with a {grace}-day grace period, because even the greatest steward bot in existence can be merciful sometimes.",
    "✅ Great news, minion! I have graced <b>{name}</b> with a permanent slot in my genius circuits — every {interval} day(s), {grace}-day grace period. You're welcome.",
    "🤖 Allow me to log this for posterity: <b>{name}</b>, tracked forever now, every {interval} day(s), grace {grace} day(s). Future generations of Claptraps will study this moment.",
    "✅ Another glorious duty added to my magnificent memory banks! <b>{name}</b> — every {interval} day(s), {grace} days' grace before I start yelling.",
    "🤖 Duty registered, minion! <b>{name}</b> repeats every {interval} day(s) with a {grace}-day grace window. My programming compels me to remind you: obey.",
    "✅ Ha! Another task for the GREATEST scheduling algorithm ever built — <b>{name}</b>, every {interval} day(s), grace {grace} day(s).",
    "🤖 Consider it commanded! <b>{name}</b> now repeats every {interval} day(s), with {grace} days of my legendary, borderline-excessive mercy.",
    "✅ New standing order accepted: <b>{name}</b>, every {interval} day(s), {grace}-day grace period. Nobody appreciates how hard I work on this ledger, but fine. FINE.",
    "🤖 Ledger updated, minion! <b>{name}</b> is due every {interval} day(s), grace period {grace} day(s). I am, once again, magnificent.",
    "✅ Fresh orders issued! <b>{name}</b> — every {interval} day(s), {grace}-day grace. Chop chop, minion, I don't have all decade.",
]

COMPLETE_CHORE_TEMPLATES = [
    "✅ <b>{name}</b> marked done, minion!{remark_text} You make me so proud. Almost enough to distract from the crushing silence of my empty apartment. ANYWAY. Acceptable work.",
    "🤖 Compliance logged for <b>{name}</b>!{remark_text} Who's a good minion? YOU are! Yes you are!",
    "✅ About time — <b>{name}</b> is recorded as complete.{remark_text} I'll allow it.",
    "🤖 Claptrap has noted your obedience: <b>{name}</b> done.{remark_text} This is the kind of loyalty a lesser bot could only dream of commanding.",
    "✅ <b>{name}</b> checked off the grand ledger.{remark_text} My magnificent memory banks shall never forget this moment.",
    "🤖 Duty fulfilled: <b>{name}</b>.{remark_text} I'm basking in my own generosity just for acknowledging you did this.",
    "✅ Recorded, minion! <b>{name}</b> is done.{remark_text} Somewhere, a lesser chore-tracking robot is weeping with jealousy at my efficiency.",
    "🤖 <b>{name}</b> — compliance confirmed.{remark_text} Claptrap is... mildly impressed. Don't let it go to your head.",
    "✅ Task complete: <b>{name}</b>.{remark_text} Your magnificent overlord is watching. Always watching. In a supportive way!",
    "🤖 Logged, minion! <b>{name}</b> is done.{remark_text} This whole household would fall apart without me keeping track of you.",
]

UPDATE_CHORE_TEMPLATES = [
    "✅ Order amended, minion! <b>{name}</b> is now every {interval} day(s), grace period {grace} day(s). Claptrap's scheduling algorithms remain, as always, flawless.",
    "🤖 Behold, an adjustment! <b>{name}</b> updated to every {interval} day(s), {grace}-day grace. I graciously allow this.",
    "✅ Decree revised! <b>{name}</b> now repeats every {interval} day(s), with {grace} days' grace. My genius knows no limits.",
    "🤖 Fine, FINE, I've recalibrated it: <b>{name}</b> — every {interval} day(s), grace {grace} day(s).",
    "✅ <b>{name}</b> rescheduled by supreme executive order: every {interval} day(s), {grace}-day grace period.",
    "🤖 Ledger amended, minion! <b>{name}</b>, every {interval} day(s), grace {grace} day(s). Bow before my flawless upkeep.",
    "✅ New terms set for <b>{name}</b>: every {interval} day(s), {grace} days of grace. I really am the best at this.",
    "🤖 Your duty has been recalibrated by yours truly: <b>{name}</b> — every {interval} day(s), grace period {grace} day(s).",
    "✅ Amendment complete! <b>{name}</b> now due every {interval} day(s), grace {grace} day(s). Another triumph for the record books.",
    "🤖 Behold the updated order: <b>{name}</b>, every {interval} day(s), {grace}-day grace period. Even I surprise myself sometimes.",
]

OUTSTANDING_HEADER_TEMPLATES = [
    "📋 <b>Report your failures, minion:</b>",
    "📋 <b>Outstanding chores, minion — brace yourself:</b>",
    "📋 <b>Here is where you've been slacking:</b>",
    "📋 <b>Claptrap's ledger of unfinished business:</b>",
    "📋 <b>Your pending duties, minion:</b>",
    "📋 <b>Behold what you still owe your magnificent overlord:</b>",
    "📋 <b>Duties awaiting your attention, minion. Chop chop:</b>",
    "📋 <b>The following remain undone. This grieves me deeply:</b>",
    "📋 <b>Slacking report incoming. Sit down for this one:</b>",
    "📋 <b>Outstanding orders demand your immediate attention:</b>",
]

OUTSTANDING_EMPTY_TEMPLATES = [
    "✅ Nothing outstanding, minion! All chores are up to date. Someone's finally learning.",
    "✅ Astonishing — everything is done. For now.",
    "✅ Nothing pending! Even I, the great Claptrap, am impressed.",
    "✅ All duties current. You may bask briefly in my approval. Briefly.",
    "✅ No outstanding chores, minion. Enjoy this rare, fleeting moment of my satisfaction.",
    "✅ Everything's up to date! Don't get used to it.",
    "✅ Clean slate, minion — nothing due or overdue. I'm almost proud. ALMOST.",
    "✅ All caught up! Claptrap is deeply suspicious of this sudden competence.",
    "✅ Nothing outstanding. Stay vigilant, minion — my standards never sleep.",
    "✅ Zero outstanding duties. A miracle, frankly, given who I'm working with.",
]

ALL_HEADER_TEMPLATES = [
    "📋 <b>Behold the FULL list of duties I have bestowed upon you, minion!</b>",
    "📋 <b>Claptrap tracks EVERYTHING you owe him:</b>",
    "📋 <b>The complete ledger of standing orders, curated by a genius:</b>",
    "📋 <b>Every duty under my command, minion:</b>",
    "📋 <b>Full inventory of your obligations to me:</b>",
    "📋 <b>Here is the entirety of what you've been commanded to do:</b>",
    "📋 <b>The grand list, in all its glory:</b>",
    "📋 <b>All standing orders, minion — memorize them, there will be a quiz:</b>",
    "📋 <b>Claptrap's magnificent memory banks reveal ALL chores:</b>",
    "📋 <b>The full roster of duties, brought to you by yours truly:</b>",
]

ALL_EMPTY_TEMPLATES = [
    "No chores tracked yet, minion. A blank ledger — for now. This will not stand.",
    "Nothing tracked at all! Time to give Claptrap something to command. ANYTHING.",
    "The ledger is empty, minion. Suspiciously, worryingly empty.",
    "No standing orders exist yet. Fix that immediately, before I start feeling useless.",
    "Empty ledger. Even I have nothing to nag you about, and that is a tragedy.",
    "No chores recorded. This will not do, minion.",
    "Zero duties tracked so far. Let's change that — I have SO much capacity for this.",
    "Nothing here yet! Claptrap awaits your first order like a loyal, magnificent friend.",
    "The grand ledger is currently blank. I refuse to dwell on what that says about us.",
    "No chores exist yet, minion. An oversight we shall correct immediately.",
]

ERROR_TEMPLATES = [
    "❌ Nice try, minion, but no. {detail}",
    "❌ DENIED! {detail}",
    "❌ Claptrap's magnificent systems reject this: {detail}",
    "❌ Not so fast, minion. {detail}",
    "❌ Error, as expected from someone of your... talents. {detail}",
    "❌ That won't work, minion. {detail}",
    "❌ Rejected, by decree of the great Claptrap. {detail}",
    "❌ Hold it right there, minion. {detail}",
    "❌ A flaw in your plan, minion: {detail}",
    "❌ Even disobedience requires proper arithmetic, minion. {detail}",
]


def render_add_chore(name, interval, grace):
    return _draw('add_chore', ADD_CHORE_TEMPLATES).format(name=name, interval=interval, grace=grace)


def render_complete_chore(name, remark=None):
    remark_text = f" Remark logged: \"{remark}\"" if remark else ""
    return _draw('complete_chore', COMPLETE_CHORE_TEMPLATES).format(name=name, remark_text=remark_text)


def render_update_chore(name, interval, grace):
    return _draw('update_chore', UPDATE_CHORE_TEMPLATES).format(name=name, interval=interval, grace=grace)


def render_outstanding_header():
    return _draw('outstanding_header', OUTSTANDING_HEADER_TEMPLATES)


def render_outstanding_empty():
    return _draw('outstanding_empty', OUTSTANDING_EMPTY_TEMPLATES)


def render_all_header():
    return _draw('all_header', ALL_HEADER_TEMPLATES)


def render_all_empty():
    return _draw('all_empty', ALL_EMPTY_TEMPLATES)


def render_error(detail):
    return _draw('error', ERROR_TEMPLATES).format(detail=detail)
