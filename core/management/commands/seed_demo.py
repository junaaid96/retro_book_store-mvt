"""Idempotent: create/refresh the public demo accounts and their sample history.

    python manage.py seed_demo
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.achievements import evaluate_badges
from accounts.demo import DEMO_ACCOUNTS, DEMO_PASSWORD
from catalog.models import Book, Review
from circulation.models import Loan


class Command(BaseCommand):
    help = "Create or refresh the demo Reader and Librarian accounts (safe to re-run)."

    @transaction.atomic
    def handle(self, *args, **options):
        if not Book.objects.exists():
            call_command("seed_library", "--demo")
        books = list(Book.objects.all())
        rng = random.Random(2026)
        now = timezone.now()
        for acc in DEMO_ACCOUNTS:
            user, _ = User.objects.get_or_create(username=acc["username"])
            user.first_name, user.last_name = acc["first_name"], acc["last_name"]
            user.email = f"{acc['username']}@demo.retrobookstore"
            user.is_active = True
            user.is_superuser = False
            user.is_staff = acc["label"] == "Librarian"
            user.set_password(DEMO_PASSWORD)
            user.save()
            profile = user.profile
            profile.balance = Decimal("40")
            profile.reading_goal = 24
            profile.save()
            if acc["label"] != "Reader" or user.loans.exists() or not books:
                continue
            for book in rng.sample(books, min(10, len(books))):
                borrowed = now - timedelta(days=rng.randint(20, 300))
                due = borrowed + timedelta(days=14)
                returned = borrowed + timedelta(days=rng.randint(4, 15))
                Loan.objects.create(user=user, book=book, borrowed_at=borrowed, due_at=due, returned_at=returned,
                                    fee_paid=book.borrowing_fee, refund=book.borrowing_fee / 2)
                if rng.random() < 0.6:
                    Review.objects.get_or_create(book=book, user=user, defaults={
                        "rating": rng.choice([5, 4, 4, 3]), "body": "Lovely read — borrowed it on a whim and finished it in a weekend."})
            for book in rng.sample(books, min(2, len(books))):
                if not Loan.objects.filter(user=user, book=book).exists():
                    borrowed = now - timedelta(days=rng.randint(1, 6))
                    Loan.objects.create(user=user, book=book, borrowed_at=borrowed,
                                        due_at=borrowed + timedelta(days=14), fee_paid=book.borrowing_fee)
            profile.xp = user.loans.count() * 10 + user.reviews.count() * 20
            profile.save(update_fields=["xp"])
            evaluate_badges(user)
            user.notifications.all().delete()
        self.stdout.write(self.style.SUCCESS("Demo accounts ready: " + ", ".join(a["username"] for a in DEMO_ACCOUNTS)))
