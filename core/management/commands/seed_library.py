import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from accounts.achievements import evaluate_badges
from catalog.models import Author, Book, Genre, Mood, Review
from circulation.models import Loan
from core.seed_data import BOOKS, GENRES, MOODS

DEMO_READERS = ["ava_reads", "noah.pages", "mira_ink", "leo_margins", "zara.shelves", "kai_chapters"]
REVIEW_LINES = {
    5: ["Couldn't put it down. Already recommending it to everyone.", "An instant favourite — the ending floored me.",
        "Worth every minute. I'll be rereading this."],
    4: ["Really enjoyed this one, a few slow bits in the middle.", "Great characters and a satisfying finish.",
        "Smart, warm and surprisingly funny."],
    3: ["Solid read, though it didn't fully click for me.", "Good ideas, uneven pacing."],
    2: ["Not quite for me, but I see the appeal."],
}


class Command(BaseCommand):
    help = "Load the starter catalogue. Use --demo to add sample readers, loans and reviews."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Also create demo readers with history.")

    @transaction.atomic
    def handle(self, *args, demo=False, **options):
        genres = {n: Genre.objects.get_or_create(name=n, defaults={"slug": slugify(n), "emoji": e})[0]
                  for n, e in GENRES}
        moods = {n: Mood.objects.get_or_create(name=n, defaults={"slug": slugify(n), "emoji": e})[0]
                 for n, e in MOODS}
        created = 0
        for (title, author, isbn, year, pages, pace, fee, copies, g, m, teaser, desc, featured) in BOOKS:
            author_obj, _ = Author.objects.get_or_create(name=author)
            book, is_new = Book.objects.get_or_create(
                slug=slugify(title),
                defaults=dict(
                    title=title, author=author_obj, isbn=isbn, published_year=year, pages=pages, pace=pace,
                    borrowing_fee=Decimal(fee), total_copies=copies, blind_date_teaser=teaser,
                    description=desc, is_featured=featured,
                ),
            )
            if is_new:
                book.genres.set([genres[x] for x in g])
                book.moods.set([moods[x] for x in m])
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Catalogue ready: {Book.objects.count()} books ({created} new)."))

        if demo:
            self._demo()

    def _demo(self):
        rng = random.Random(42)
        books = list(Book.objects.all())
        now = timezone.now()
        for i, username in enumerate(DEMO_READERS):
            user, is_new = User.objects.get_or_create(
                username=username, defaults={"first_name": username.split("_")[0].split(".")[0].title()}
            )
            if not is_new:
                continue
            user.set_unusable_password()
            user.save()
            profile = user.profile
            profile.balance = Decimal(rng.choice([12, 20, 35, 50]))
            profile.reading_goal = rng.choice([12, 20, 24])
            profile.save()

            for book in rng.sample(books, rng.randint(4, 12)):
                borrowed = now - timedelta(days=rng.randint(15, 330))
                due = borrowed + timedelta(days=14)
                returned = borrowed + timedelta(days=rng.randint(3, 16))
                late_days = max((returned.date() - due.date()).days, 0)
                Loan.objects.create(
                    user=user, book=book, borrowed_at=borrowed, due_at=due, returned_at=returned,
                    fee_paid=book.borrowing_fee, refund=book.borrowing_fee / 2,
                    late_fee=Decimal("0.50") * late_days,
                )
                if rng.random() < 0.7:
                    rating = rng.choices([5, 4, 3, 2], weights=[5, 4, 2, 1])[0]
                    Review.objects.get_or_create(
                        book=book, user=user,
                        defaults={"rating": rating, "body": rng.choice(REVIEW_LINES[rating])},
                    )
            # A couple of recent loans so "Trending" has something to show.
            for book in rng.sample(books, 2):
                if not Loan.objects.filter(user=user, book=book).exists():
                    borrowed = now - timedelta(days=rng.randint(1, 10))
                    Loan.objects.create(user=user, book=book, borrowed_at=borrowed,
                                        due_at=borrowed + timedelta(days=14), fee_paid=book.borrowing_fee)
            loans = user.loans.count()
            profile.xp = loans * 10 + user.reviews.count() * 20 + i * 15
            profile.save(update_fields=["xp"])
            evaluate_badges(user)
            user.notifications.all().delete()
        self.stdout.write(self.style.SUCCESS(f"Demo readers ready: {len(DEMO_READERS)}."))
