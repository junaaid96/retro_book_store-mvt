from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from catalog.models import Book


class LoanQuerySet(models.QuerySet):
    def active(self):
        return self.filter(returned_at__isnull=True)

    def overdue(self):
        return self.active().filter(due_at__lt=timezone.now())


class Loan(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="loans", on_delete=models.CASCADE)
    book = models.ForeignKey(Book, related_name="loans", on_delete=models.PROTECT)
    borrowed_at = models.DateTimeField(default=timezone.now)
    due_at = models.DateTimeField()
    returned_at = models.DateTimeField(null=True, blank=True)
    renewals = models.PositiveSmallIntegerField(default=0)
    fee_paid = models.DecimalField(max_digits=8, decimal_places=2)
    refund = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    late_fee = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    via_blind_date = models.BooleanField(default=False)
    due_reminder_sent = models.BooleanField(default=False)
    overdue_notice_sent = models.BooleanField(default=False)

    objects = LoanQuerySet.as_manager()

    class Meta:
        ordering = ["-borrowed_at"]
        indexes = [
            models.Index(fields=["user", "returned_at"]),
            models.Index(fields=["book", "returned_at"]),
            models.Index(fields=["due_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "book"],
                condition=Q(returned_at__isnull=True),
                name="one_active_loan_per_book",
            )
        ]

    def __str__(self):
        return f"{self.user} → {self.book.title}"

    @property
    def is_active(self):
        return self.returned_at is None

    @property
    def is_overdue(self):
        return self.is_active and self.due_at < timezone.now()

    @property
    def days_left(self):
        return (self.due_at.date() - timezone.localdate()).days

    @property
    def days_late(self):
        return max(-self.days_left, 0)

    @property
    def progress_percent(self):
        """How far through the loan period we are, for the due-date bar."""
        total = (self.due_at - self.borrowed_at).total_seconds() or 1
        elapsed = (timezone.now() - self.borrowed_at).total_seconds()
        return max(0, min(100, round(elapsed / total * 100)))

    @property
    def returned_on_time(self):
        return self.returned_at is not None and not self.late_fee


class Hold(models.Model):
    """A place in the waitlist for a book with no free copies."""

    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting"
        READY = "ready", "Ready for pickup"
        FULFILLED = "fulfilled", "Fulfilled"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="holds", on_delete=models.CASCADE)
    book = models.ForeignKey(Book, related_name="holds", on_delete=models.CASCADE)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.WAITING)
    created_at = models.DateTimeField(default=timezone.now)
    ready_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["book", "status", "created_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "book"],
                condition=Q(status__in=["waiting", "ready"]),
                name="one_open_hold_per_book",
            )
        ]

    def __str__(self):
        return f"{self.user} ⏳ {self.book.title} ({self.status})"

    @property
    def position(self):
        if self.status != self.Status.WAITING:
            return 0
        return (
            Hold.objects.filter(
                book=self.book, status=self.Status.WAITING, created_at__lt=self.created_at
            ).count()
            + 1
        )
