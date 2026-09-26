from collections import Counter
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from catalog.discovery import recommended_for
from catalog.models import Book
from circulation.models import Hold, Loan
from circulation.services import send_reminders

from .achievements import BADGES, evaluate_badges
from .forms import DepositForm, LoginForm, ProfileForm, RegisterForm, UserForm
from .models import Profile, Transaction
from .services import WalletError, deposit

QUICK_AMOUNTS = [5, 10, 25, 50]


def sum_or_zero(condition):
    return Coalesce(Sum("amount", filter=condition), Value(Decimal("0")))


def _safe_next(request, fallback):
    nxt = request.GET.get("next") or request.POST.get("next") or ""
    return nxt if nxt.startswith("/") and not nxt.startswith("//") else fallback


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
        except IntegrityError as error:
            constraint = getattr(getattr(error.__cause__, "diag", None), "constraint_name", None)
            if constraint != "auth_user_username_key":
                raise
            form.add_error("username", "That username is already in use. Please choose another.")
        else:
            login(request, user)
            messages.success(request, f"Welcome to RetroBookStore, {user.first_name}! Top up your wallet to borrow your first book.")
            return redirect("dashboard")
    return render(request, "accounts/register.html", {"form": form})


class RetroLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


def borrow_streak(user):
    """Consecutive months (ending this month or last) with at least one borrow."""
    months = {(d.year, d.month) for d in user.loans.values_list("borrowed_at", flat=True)}
    today = timezone.localdate()
    y, m = today.year, today.month
    if (y, m) not in months:
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    streak = 0
    while (y, m) in months:
        streak += 1
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return streak


@login_required
def dashboard(request):
    user = request.user
    send_reminders(Loan.objects.active().filter(user=user).select_related("book", "user"))
    evaluate_badges(user)
    profile = Profile.objects.get(user=user)

    active = Loan.objects.active().filter(user=user).select_related("book", "book__author").order_by("due_at")
    holds = (
        Hold.objects.filter(user=user, status__in=[Hold.Status.WAITING, Hold.Status.READY])
        .select_related("book", "book__author")
        .order_by("status", "created_at")
    )
    year = timezone.localdate().year
    finished_this_year = user.loans.filter(returned_at__year=year).count()
    goal = profile.reading_goal or 1
    owned = {b.code: b for b in user.badges.all()}
    badges = [
        {"code": code, **meta, "earned": owned.get(code)} for code, meta in BADGES.items()
    ]
    context = {
        "profile": profile,
        "active_loans": active,
        "holds": holds,
        "finished_this_year": finished_this_year,
        "goal_percent": min(100, round(finished_this_year / goal * 100)),
        "streak": borrow_streak(user),
        "badges": badges,
        "badges_earned": len(owned),
        "for_you": recommended_for(user, limit=6),
        "recent_tx": user.transactions.all()[:5],
        "year": year,
    }
    return render(request, "accounts/dashboard.html", context)


@login_required
def wallet(request):
    form = DepositForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            deposit(request.user, form.cleaned_data["amount"])
        except WalletError as e:
            messages.error(request, str(e))
        else:
            messages.success(request, "Wallet topped up! 💰")
            return redirect(_safe_next(request, reverse("wallet")))
    tx = request.user.transactions.all()
    kind = request.GET.get("kind")
    if kind in Transaction.Kind.values:
        tx = tx.filter(kind=kind)
    totals = request.user.transactions.aggregate(
        spent=-sum_or_zero(Q(amount__lt=0)), earned=sum_or_zero(Q(amount__gt=0) & ~Q(kind="deposit"))
    )
    context = {
        "form": form,
        "page": Paginator(tx, 20).get_page(request.GET.get("page")),
        "quick_amounts": QUICK_AMOUNTS,
        "kinds": Transaction.Kind.choices,
        "kind": kind,
        "totals": totals,
        "next": _safe_next(request, ""),
    }
    return render(request, "accounts/wallet.html", context)


@login_required
def settings_view(request):
    user_form = UserForm(request.POST or None, instance=request.user, prefix="u")
    profile_form = ProfileForm(request.POST or None, instance=request.user.profile, prefix="p")
    if request.method == "POST" and user_form.is_valid() and profile_form.is_valid():
        user_form.save()
        profile_form.save()
        messages.success(request, "Settings saved.")
        return redirect("settings")
    return render(request, "accounts/settings.html", {"user_form": user_form, "profile_form": profile_form})


@login_required
def notifications(request):
    items = request.user.notifications.all()[:50]
    response = render(request, "accounts/notifications.html", {"items": items})
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return response


@login_required
@require_POST
def notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect(_safe_next(request, reverse("notifications")))


@login_required
def shelf(request):
    books = Book.objects.with_stats().select_related("author").filter(shelved_by__user=request.user).order_by(
        "-shelved_by__created_at"
    )
    return render(request, "accounts/shelf.html", {"books": books})


@login_required
def history(request):
    loans = request.user.loans.select_related("book", "book__author").order_by("-borrowed_at")
    return render(request, "accounts/history.html", {"page": Paginator(loans, 20).get_page(request.GET.get("page"))})


PERSONA_ADJ = {
    "adventurous": "Adventurous", "dark": "Midnight", "funny": "Cheerful", "mysterious": "Curious",
    "emotional": "Tender-hearted", "hopeful": "Sunny", "reflective": "Thoughtful", "tense": "Thrill-seeking",
    "romantic": "Romantic", "informative": "Inquisitive", "inspiring": "Inspired", "lighthearted": "Breezy",
    "relaxing": "Cosy", "challenging": "Fearless", "sad": "Melancholy",
}
PERSONA_NOUN = {"fast": "Page Sprinter", "medium": "Story Wanderer", "slow": "Slow Sipper"}


@login_required
def wrapped(request, year=None):
    """A Spotify-Wrapped-style recap of a reader's year."""
    user = request.user
    year = year or timezone.localdate().year
    if year < 2000 or year > timezone.localdate().year:
        raise Http404
    loans = user.loans.filter(borrowed_at__year=year).select_related("book", "book__author")
    finished = [l for l in loans if l.returned_at]
    books = [l.book for l in loans]

    genres = Counter(g.name for b in books for g in b.genres.all())
    moods = Counter((m.slug, m.name, m.emoji) for b in books for m in b.moods.all())
    authors = Counter(b.author.name for b in books)
    paces = Counter(b.pace for b in books)
    months = [0] * 12
    for l in loans:
        months[timezone.localtime(l.borrowed_at).month - 1] += 1

    persona = None
    if moods:
        (slug, _, _), _ = moods.most_common(1)[0]
        pace = paces.most_common(1)[0][0]
        persona = f"The {PERSONA_ADJ.get(slug, 'Curious')} {PERSONA_NOUN.get(pace, 'Reader')}"

    reviews = user.reviews.filter(created_at__year=year)
    years = sorted({d.year for d in user.loans.values_list("borrowed_at", flat=True)} | {timezone.localdate().year})
    context = {
        "year": year,
        "years": years,
        "borrowed": len(loans),
        "finished": len(finished),
        "pages": sum(l.book.pages for l in finished),
        "on_time_rate": round(sum(1 for l in finished if not l.late_fee) / len(finished) * 100) if finished else None,
        "top_genres": genres.most_common(5),
        "top_moods": [(name, emoji, n) for (_, name, emoji), n in moods.most_common(5)],
        "top_author": authors.most_common(1)[0] if authors else None,
        "longest": max(books, key=lambda b: b.pages, default=None),
        "blind_dates": sum(1 for l in loans if l.via_blind_date),
        "avg_rating": reviews.aggregate(a=Avg("rating"))["a"],
        "review_count": reviews.count(),
        "months": months,
        "month_labels": ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"],
        "month_max": max(months) or 1,
        "persona": persona,
        "covers": books[:12],
    }
    return render(request, "accounts/wrapped.html", context)


def leaderboard(request):
    month_start = timezone.localdate().replace(day=1)
    readers = (
        Profile.objects.select_related("user")
        .annotate(
            month_books=Count("user__loans", filter=Q(user__loans__borrowed_at__date__gte=month_start), distinct=True),
            badge_count=Count("user__badges", distinct=True),
        )
        .filter(xp__gt=0)
        .order_by("-xp", "user__username")[:25]
    )
    return render(request, "accounts/leaderboard.html", {"readers": readers})
