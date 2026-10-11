"""Public demo accounts shown on the login page ("Explore the demo").

The password is intentionally public. Demo users are protected server-side:
their email can't be changed and they never get superuser rights.
"""

DEMO_PASSWORD = "RetroDemo!2026"
DEMO_ACCOUNTS = [
    {"username": "demo_reader", "label": "Reader", "icon": "📚", "first_name": "Demo", "last_name": "Reader"},
    {"username": "demo_librarian", "label": "Librarian", "icon": "🛠️", "first_name": "Demo", "last_name": "Librarian"},
]
DEMO_USERNAMES = {a["username"] for a in DEMO_ACCOUNTS}


def is_demo(user):
    return bool(getattr(user, "is_authenticated", False)) and user.username in DEMO_USERNAMES
