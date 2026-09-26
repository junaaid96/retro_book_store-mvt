import logging
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import F
from django.template.loader import render_to_string
from django.urls import reverse

from .models import Notification, Profile, Transaction

log = logging.getLogger(__name__)

MAX_DEPOSIT = Decimal("10000")


class WalletError(Exception):
    pass


def post_transaction(profile, kind, amount, note=""):
    """Apply a signed amount to a *locked* profile and record it in the ledger."""
    profile.balance += amount
    profile.save(update_fields=["balance"])
    return Transaction.objects.create(
        user=profile.user, kind=kind, amount=amount, balance_after=profile.balance, note=note[:200]
    )


def deposit(user, amount):
    amount = Decimal(amount)
    if amount <= 0 or amount > MAX_DEPOSIT:
        raise WalletError(f"Deposits must be between 0.01 and {MAX_DEPOSIT:,.0f}.")
    with transaction.atomic():
        profile = Profile.objects.select_for_update().get(user=user)
        tx = post_transaction(profile, Transaction.Kind.DEPOSIT, amount, "Wallet top-up")
    notify(
        user,
        Notification.Kind.WALLET,
        f"{settings.LIBRARY['CURRENCY']}{amount:,.2f} added to your wallet",
        f"New balance: {settings.LIBRARY['CURRENCY']}{tx.balance_after:,.2f}",
        url=reverse("wallet"),
        email=True,
    )
    return tx


def add_xp(user, points):
    Profile.objects.filter(user=user).update(xp=F("xp") + points)


def notify(user, kind, title, body="", url="", email=False):
    note = Notification.objects.create(user=user, kind=kind, title=title, body=body, url=url)
    if email and user.email and getattr(user, "profile", None) and user.profile.email_notifications:
        transaction.on_commit(lambda: _send_email(user, title, body, url))
    return note


def _send_email(user, title, body, url):
    context = {"user": user, "title": title, "body": body, "url": url}
    html = render_to_string("emails/notification.html", context)
    text = f"{title}\n\n{body}\n"
    msg = EmailMultiAlternatives(f"RetroBookStore · {title}", text, to=[user.email])
    msg.attach_alternative(html, "text/html")
    try:
        msg.send()
    except Exception:  # Email must never break a borrow or a return.
        log.exception("Failed to send notification email to %s", user.email)
