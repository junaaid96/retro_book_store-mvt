"""
All circulation rules live here so views stay thin and every money/stock
change happens inside one database transaction with the rows locked.
"""

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from accounts.achievements import evaluate_badges
from accounts.models import Notification, Profile, Transaction
from accounts.services import add_xp, notify, post_transaction
from catalog.models import Book

from .models import Hold, Loan

XP_BORROW = 10
XP_ON_TIME = 15
XP_BLIND_DATE = 25
CENT = Decimal("0.01")


class CirculationError(Exception):
    """A rule stopped the action. The message is safe to show to the reader."""

    def __init__(self, message, code="error"):
        super().__init__(message)
        self.code = code


def policy(key):
    return settings.LIBRARY[key]


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def fee_for(book, via_blind_date=False):
    fee = book.borrowing_fee
    if via_blind_date:
        fee = fee * (1 - Decimal(policy("BLIND_DATE_DISCOUNT")))
    return money(fee)


def _free_copies(book):
    loans = Loan.objects.active().filter(book=book).count()
    ready = Hold.objects.filter(book=book, status=Hold.Status.READY).count()
    return max(book.total_copies - loans - ready, 0)


def process_holds(book):
    """Expire stale pickups and hand free copies to the next readers in line.

    The caller must hold a lock on the book row.
    """
    now = timezone.now()
    for hold in Hold.objects.filter(book=book, status=Hold.Status.READY, expires_at__lt=now):
        hold.status = Hold.Status.EXPIRED
        hold.save(update_fields=["status"])
        notify(hold.user, Notification.Kind.HOLD_EXPIRED, f"Your hold on “{book.title}” expired",
               "The copy was passed to the next reader. You can join the waitlist again.",
               url=book.get_absolute_url())

    free = _free_copies(book)
    if free <= 0:
        return
    hours = policy("HOLD_PICKUP_HOURS")
    for hold in Hold.objects.filter(book=book, status=Hold.Status.WAITING).order_by("created_at")[:free]:
        hold.status = Hold.Status.READY
        hold.ready_at = now
        hold.expires_at = now + timedelta(hours=hours)
        hold.save(update_fields=["status", "ready_at", "expires_at"])
        notify(hold.user, Notification.Kind.HOLD_READY, f"“{book.title}” is waiting for you",
               f"We've set a copy aside. Borrow it within {hours} hours to keep your spot.",
               url=book.get_absolute_url(), email=True)


def refresh_book(book):
    with transaction.atomic():
        locked = Book.objects.select_for_update().get(pk=book.pk)
        process_holds(locked)


def borrow(user, book, via_blind_date=False):
    with transaction.atomic():
        book = Book.objects.select_for_update().select_related("author").get(pk=book.pk)
        profile = Profile.objects.select_for_update().get(user=user)
        process_holds(book)

        active = Loan.objects.active().filter(user=user)
        if active.filter(book=book).exists():
            raise CirculationError("You already have this book on your shelf.", "duplicate")
        if active.filter(due_at__lt=timezone.now()).exists():
            raise CirculationError("Please return your overdue books before borrowing more.", "overdue")
        if active.count() >= policy("MAX_ACTIVE_LOANS"):
            raise CirculationError(
                f"You can have up to {policy('MAX_ACTIVE_LOANS')} books at a time. Return one first.", "limit"
            )

        my_hold = Hold.objects.filter(user=user, book=book, status=Hold.Status.READY).first()
        if not my_hold and _free_copies(book) <= 0:
            raise CirculationError("All copies are out right now. Join the waitlist and we'll save you one.",
                                   "unavailable")

        fee = fee_for(book, via_blind_date)
        if profile.balance < fee:
            raise CirculationError(
                f"You need {policy('CURRENCY')}{fee - profile.balance:,.2f} more in your wallet.", "funds"
            )

        post_transaction(profile, Transaction.Kind.BORROW, -fee,
                         "Blind date 💌" if via_blind_date else f"“{book.title}”")
        now = timezone.now()
        loan = Loan.objects.create(
            user=user, book=book, borrowed_at=now, due_at=now + timedelta(days=policy("LOAN_DAYS")),
            fee_paid=fee, via_blind_date=via_blind_date,
        )
        Hold.objects.filter(user=user, book=book, status__in=[Hold.Status.READY, Hold.Status.WAITING]).update(
            status=Hold.Status.FULFILLED
        )
        add_xp(user, XP_BORROW + (XP_BLIND_DATE if via_blind_date else 0))

    evaluate_badges(user)
    return loan


def return_loan(user, loan_id):
    with transaction.atomic():
        loan = (
            Loan.objects.select_for_update()
            .select_related("book")
            .filter(pk=loan_id, user=user, returned_at__isnull=True)
            .first()
        )
        if loan is None:
            raise CirculationError("That loan is already closed.", "closed")
        book = Book.objects.select_for_update().get(pk=loan.book_id)
        profile = Profile.objects.select_for_update().get(user=user)

        now = timezone.now()
        late_days = max((timezone.localdate(now) - timezone.localdate(loan.due_at)).days, 0)
        loan.late_fee = money(Decimal(policy("LATE_FEE_PER_DAY")) * late_days)
        loan.refund = money(loan.fee_paid * Decimal(policy("RETURN_REFUND_RATE")))
        loan.returned_at = now
        loan.save(update_fields=["late_fee", "refund", "returned_at"])

        if loan.refund:
            post_transaction(profile, Transaction.Kind.REFUND, loan.refund, f"Returned “{book.title}”")
        if loan.late_fee:
            post_transaction(profile, Transaction.Kind.LATE_FEE, -loan.late_fee,
                             f"{late_days} day(s) late · “{book.title}”")
        if loan.returned_on_time:
            add_xp(user, XP_ON_TIME)
        process_holds(book)

    evaluate_badges(user)
    return loan


def renew(user, loan_id):
    with transaction.atomic():
        loan = (
            Loan.objects.select_for_update()
            .filter(pk=loan_id, user=user, returned_at__isnull=True)
            .first()
        )
        if loan is None:
            raise CirculationError("That loan is already closed.", "closed")
        if loan.is_overdue:
            raise CirculationError("Overdue books can't be renewed. Please return it.", "overdue")
        if loan.renewals >= policy("MAX_RENEWALS"):
            raise CirculationError("You've used all renewals for this book.", "limit")
        if Hold.objects.filter(book_id=loan.book_id, status=Hold.Status.WAITING).exists():
            raise CirculationError("Other readers are waiting for this book, so it can't be renewed.", "waitlist")
        loan.due_at += timedelta(days=policy("RENEW_DAYS"))
        loan.renewals += 1
        loan.due_reminder_sent = False
        loan.save(update_fields=["due_at", "renewals", "due_reminder_sent"])
    return loan


def place_hold(user, book):
    with transaction.atomic():
        book = Book.objects.select_for_update().get(pk=book.pk)
        process_holds(book)
        if Loan.objects.active().filter(user=user, book=book).exists():
            raise CirculationError("You already have this book.", "duplicate")
        if Hold.objects.filter(user=user, book=book, status__in=[Hold.Status.WAITING, Hold.Status.READY]).exists():
            raise CirculationError("You're already on the waitlist for this book.", "duplicate")
        if _free_copies(book) > 0:
            raise CirculationError("Good news — a copy is available. Borrow it now!", "available")
        hold = Hold.objects.create(user=user, book=book)
    return hold


def cancel_hold(user, hold_id):
    with transaction.atomic():
        hold = (
            Hold.objects.select_for_update()
            .filter(pk=hold_id, user=user, status__in=[Hold.Status.WAITING, Hold.Status.READY])
            .first()
        )
        if hold is None:
            raise CirculationError("That hold is no longer active.", "closed")
        book = Book.objects.select_for_update().get(pk=hold.book_id)
        hold.status = Hold.Status.CANCELLED
        hold.save(update_fields=["status"])
        process_holds(book)
    return hold


def send_reminders(loans=None):
    """Create due-soon and overdue notices once per loan. Safe to run repeatedly."""
    loans = Loan.objects.active().select_related("book", "user") if loans is None else loans
    now = timezone.now()
    soon = now + timedelta(days=policy("DUE_SOON_DAYS"))
    sent = 0
    for loan in loans.filter(due_reminder_sent=False, due_at__gte=now, due_at__lte=soon):
        notify(loan.user, Notification.Kind.DUE_SOON, f"“{loan.book.title}” is due soon",
               f"Due {timezone.localtime(loan.due_at):%a %d %b}. Renew or return it from your dashboard.",
               url=reverse("dashboard"), email=True)
        Loan.objects.filter(pk=loan.pk).update(due_reminder_sent=True)
        sent += 1
    for loan in loans.filter(overdue_notice_sent=False, due_at__lt=now):
        notify(loan.user, Notification.Kind.OVERDUE, f"“{loan.book.title}” is overdue",
               f"Late fees are {policy('CURRENCY')}{policy('LATE_FEE_PER_DAY')} per day. Please return it soon.",
               url=reverse("dashboard"), email=True)
        Loan.objects.filter(pk=loan.pk).update(overdue_notice_sent=True)
        sent += 1
    return sent


def sweep_holds():
    """Expire stale holds and promote the waitlist for every book with open holds."""
    book_ids = Hold.objects.filter(status__in=[Hold.Status.READY, Hold.Status.WAITING]).values_list(
        "book_id", flat=True).distinct()
    for book in Book.objects.filter(pk__in=list(book_ids)):
        refresh_book(book)
