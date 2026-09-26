"""Badges readers unlock through their borrowing history."""

from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from .models import Notification, UserBadge
from .services import add_xp, notify

BADGE_XP = 50

BADGES = {
    "first_chapter": {"name": "First Chapter", "emoji": "📖", "description": "Borrow your first book."},
    "bookworm": {"name": "Bookworm", "emoji": "🐛", "description": "Finish 10 books."},
    "genre_explorer": {"name": "Genre Explorer", "emoji": "🧭", "description": "Borrow from 5 different genres."},
    "mood_ring": {"name": "Mood Ring", "emoji": "💍", "description": "Read books spanning 6 different moods."},
    "critic": {"name": "The Critic", "emoji": "🖋️", "description": "Write 5 reviews."},
    "punctual": {"name": "Right On Time", "emoji": "⏱️", "description": "Return 5 books before they're due."},
    "blind_dater": {"name": "Blind Dater", "emoji": "💌", "description": "Take a Blind Date with a Book."},
    "patient_reader": {"name": "Patient Reader", "emoji": "🪴", "description": "Get a book from the waitlist."},
    "goal_getter": {"name": "Goal Getter", "emoji": "🏆", "description": "Hit your yearly reading goal."},
    "marathoner": {"name": "Marathoner", "emoji": "🏃", "description": "Finish 3,000 pages in total."},
}


def reader_stats(user):
    from circulation.models import Hold, Loan

    loans = Loan.objects.filter(user=user)
    returned = loans.filter(returned_at__isnull=False)
    year = timezone.localdate().year
    return {
        "borrowed": loans.count(),
        "finished": returned.count(),
        "finished_this_year": returned.filter(returned_at__year=year).count(),
        "on_time": returned.filter(late_fee=0).count(),
        "genres": loans.values("book__genres").distinct().count(),
        "moods": loans.exclude(book__moods=None).values("book__moods").distinct().count(),
        "reviews": user.reviews.count(),
        "blind_dates": loans.filter(via_blind_date=True).count(),
        "holds_fulfilled": Hold.objects.filter(user=user, status=Hold.Status.FULFILLED).count(),
        "pages": sum(returned.values_list("book__pages", flat=True)),
        "goal": user.profile.reading_goal,
    }


RULES = {
    "first_chapter": lambda s: s["borrowed"] >= 1,
    "bookworm": lambda s: s["finished"] >= 10,
    "genre_explorer": lambda s: s["genres"] >= 5,
    "mood_ring": lambda s: s["moods"] >= 6,
    "critic": lambda s: s["reviews"] >= 5,
    "punctual": lambda s: s["on_time"] >= 5,
    "blind_dater": lambda s: s["blind_dates"] >= 1,
    "patient_reader": lambda s: s["holds_fulfilled"] >= 1,
    "goal_getter": lambda s: s["goal"] > 0 and s["finished_this_year"] >= s["goal"],
    "marathoner": lambda s: s["pages"] >= 3000,
}


def evaluate_badges(user):
    """Award any newly earned badges. Returns the list of new badge codes."""
    owned = set(user.badges.values_list("code", flat=True))
    pending = [code for code in RULES if code not in owned]
    if not pending:
        return []
    stats = reader_stats(user)
    earned = []
    for code in pending:
        if not RULES[code](stats):
            continue
        try:
            with transaction.atomic():
                UserBadge.objects.create(user=user, code=code)
        except IntegrityError:
            continue
        badge = BADGES[code]
        add_xp(user, BADGE_XP)
        notify(user, Notification.Kind.BADGE, f"Badge unlocked: {badge['emoji']} {badge['name']}",
               badge["description"], url=reverse("dashboard") + "#badges")
        earned.append(code)
    return earned
