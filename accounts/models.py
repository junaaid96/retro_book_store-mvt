from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse

LEVELS = [
    (0, "Page Turner"),
    (100, "Bookworm"),
    (300, "Bibliophile"),
    (700, "Archivist"),
    (1500, "Librarian of Legend"),
]


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="profile", on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    xp = models.PositiveIntegerField(default=0)
    reading_goal = models.PositiveSmallIntegerField(default=12, help_text="Books to finish this year.")
    bio = models.CharField(max_length=160, blank=True)
    address = models.CharField(max_length=200, blank=True)
    favorite_genres = models.ManyToManyField("catalog.Genre", blank=True, related_name="fans")
    email_notifications = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.balance})"

    @property
    def level_info(self):
        idx = max(i for i, (threshold, _) in enumerate(LEVELS) if self.xp >= threshold)
        floor, title = LEVELS[idx]
        ceiling = LEVELS[idx + 1][0] if idx + 1 < len(LEVELS) else None
        pct = 100 if ceiling is None else round((self.xp - floor) / (ceiling - floor) * 100)
        return {"level": idx + 1, "title": title, "next_at": ceiling, "percent": pct}

    @property
    def initials(self):
        u = self.user
        return ((u.first_name[:1] + u.last_name[:1]) or u.username[:2]).upper()


class Transaction(models.Model):
    class Kind(models.TextChoices):
        DEPOSIT = "deposit", "Deposit"
        BORROW = "borrow", "Borrowing fee"
        REFUND = "refund", "Return refund"
        LATE_FEE = "late_fee", "Late fee"
        RENEWAL = "renewal", "Renewal"
        BONUS = "bonus", "Bonus"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="transactions", on_delete=models.CASCADE)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Positive = credit, negative = debit.")
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"{self.user} {self.kind} {self.amount}"


class Notification(models.Model):
    class Kind(models.TextChoices):
        HOLD_READY = "hold_ready", "Hold ready"
        HOLD_EXPIRED = "hold_expired", "Hold expired"
        DUE_SOON = "due_soon", "Due soon"
        OVERDUE = "overdue", "Overdue"
        BADGE = "badge", "Badge earned"
        WALLET = "wallet", "Wallet"
        INFO = "info", "Info"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="notifications", on_delete=models.CASCADE)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.INFO)
    title = models.CharField(max_length=140)
    body = models.CharField(max_length=300, blank=True)
    url = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read"])]

    def __str__(self):
        return self.title

    @property
    def icon(self):
        return {
            "hold_ready": "📬", "hold_expired": "⌛", "due_soon": "⏰", "overdue": "🚨",
            "badge": "🏅", "wallet": "💰",
        }.get(self.kind, "🔔")


class UserBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="badges", on_delete=models.CASCADE)
    code = models.CharField(max_length=40)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-awarded_at"]
        constraints = [models.UniqueConstraint(fields=["user", "code"], name="unique_badge")]

    def __str__(self):
        return f"{self.user} · {self.code}"

    @property
    def meta(self):
        from .achievements import BADGES

        return BADGES.get(self.code)

    def get_absolute_url(self):
        return reverse("dashboard") + "#badges"
