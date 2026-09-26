import random
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import Profile
from circulation.models import Hold, Loan
from circulation.services import fee_for, policy, refresh_book

from .discovery import SORTS, also_borrowed, filter_books, recommended_for, search_books, similar_books
from .forms import ReviewForm
from .models import Author, Book, Genre, Mood, Review, ShelfItem


def is_htmx(request):
    return request.headers.get("HX-Request") == "true"


def home(request):
    books = Book.objects.with_stats().select_related("author")
    month_ago = timezone.now() - timedelta(days=30)
    trending = (
        books.annotate(recent=Count("loans", filter=Q(loans__borrowed_at__gte=month_ago)))
        .order_by("-recent", "-times_borrowed", "title")[:10]
    )
    context = {
        "trending": trending,
        "featured": books.filter(is_featured=True).order_by("?")[:6],
        "new_arrivals": books.order_by("-created_at")[:10],
        "top_rated": books.filter(review_count__gt=0).order_by(F("avg_rating").desc(nulls_last=True))[:6],
        "genres": Genre.objects.annotate(n=Count("books")).filter(n__gt=0).order_by("-n")[:12],
        "moods": Mood.objects.all(),
        "stats": {
            "books": Book.objects.count(),
            "readers": Profile.objects.count(),
            "loans": Loan.objects.count(),
        },
        "top_readers": Profile.objects.select_related("user").filter(xp__gt=0).order_by("-xp")[:5],
    }
    if request.user.is_authenticated:
        context["for_you"] = recommended_for(request.user, limit=10)
    return render(request, "catalog/home.html", context)


def browse(request):
    qs, sort = filter_books(request.GET)
    page = Paginator(qs, 24).get_page(request.GET.get("page"))
    context = {
        "page": page,
        "sort": sort,
        "sorts": SORTS,
        "q": request.GET.get("q", ""),
        "genres": Genre.objects.all(),
        "moods": Mood.objects.all(),
        "paces": Book.Pace.choices,
        "selected_genres": request.GET.getlist("genre"),
        "selected_moods": request.GET.getlist("mood"),
        "selected_pace": request.GET.get("pace", ""),
    }
    template = "catalog/partials/results.html" if is_htmx(request) else "catalog/browse.html"
    return render(request, template, context)


def suggest(request):
    """Instant search dropdown in the navbar."""
    q = request.GET.get("q", "").strip()
    books = []
    if len(q) >= 2:
        books = (
            search_books(Book.objects.select_related("author"), q)
            .order_by("-rank", "-fuzzy", "title")
            .distinct()[:6]
        )
    authors = Author.objects.filter(name__icontains=q)[:3] if len(q) >= 2 else []
    return render(request, "catalog/partials/suggest.html", {"books": books, "authors": authors, "q": q})


def book_detail(request, slug):
    book = get_object_or_404(Book.objects.select_related("author"), slug=slug)
    if book.holds.filter(status__in=[Hold.Status.READY, Hold.Status.WAITING]).exists():
        refresh_book(book)  # expire stale pickups lazily
    book = Book.objects.with_stats().select_related("author").prefetch_related("genres", "moods").get(pk=book.pk)

    reviews = book.reviews.select_related("user", "user__profile")
    distribution = {r["rating"]: r["n"] for r in reviews.values("rating").annotate(n=Count("pk"))}
    total = sum(distribution.values()) or 1
    rating_bars = [(s, distribution.get(s, 0), round(distribution.get(s, 0) / total * 100)) for s in range(5, 0, -1)]

    next_due = book.loans.filter(returned_at__isnull=True).order_by("due_at").values_list("due_at", flat=True).first()
    context = {
        "book": book,
        "reviews": reviews[:20],
        "rating_bars": rating_bars,
        "similar": similar_books(book),
        "also": also_borrowed(book),
        "next_due": next_due,
        "fee": fee_for(book),
        "loan_days": policy("LOAN_DAYS"),
    }
    user = request.user
    if user.is_authenticated:
        my_loans = book.loans.filter(user=user)
        my_review = book.reviews.filter(user=user).first()
        blind = my_loans.filter(via_blind_date=True).exists()
        context.update(
            {
                "active_loan": my_loans.filter(returned_at__isnull=True).first(),
                "my_hold": book.holds.filter(user=user, status__in=[Hold.Status.READY, Hold.Status.WAITING]).first(),
                "on_shelf": ShelfItem.objects.filter(user=user, book=book).exists(),
                "can_review": my_loans.exists(),
                "my_review": my_review,
                "review_form": ReviewForm(instance=my_review, blind_date=blind),
                "balance": user.profile.balance,
            }
        )
    return render(request, "catalog/book_detail.html", context)


def author_detail(request, slug):
    author = get_object_or_404(Author, slug=slug)
    books = Book.objects.with_stats().filter(author=author).select_related("author")
    return render(request, "catalog/author_detail.html", {"author": author, "books": books})


def discover(request):
    """Pick a mood (and pace), get a shelf that matches."""
    moods = Mood.objects.annotate(n=Count("books")).filter(n__gt=0)
    selected = request.GET.getlist("mood")
    pace = request.GET.get("pace", "")
    results = None
    if selected or pace:
        qs = Book.objects.with_stats().select_related("author")
        if selected:
            qs = qs.annotate(
                match=Count("moods", filter=Q(moods__slug__in=selected), distinct=True)
            ).filter(match__gt=0)
        if pace in Book.Pace.values:
            qs = qs.filter(pace=pace)
        order = ["-match", "-times_borrowed"] if selected else ["-times_borrowed"]
        results = qs.order_by(*order)[:24]
    context = {"moods": moods, "selected": selected, "pace": pace, "paces": Book.Pace.choices, "results": results}
    template = "catalog/partials/discover_results.html" if is_htmx(request) else "catalog/discover.html"
    return render(request, template, context)


def blind_date(request):
    """Three wrapped books described only by spoiler-free hints."""
    qs = Book.objects.with_stats().exclude(blind_date_teaser="").prefetch_related("genres", "moods")
    qs = qs.filter(total_copies__gt=F("active_loans") + F("reserved") + F("waiting"))
    if request.user.is_authenticated:
        qs = qs.exclude(loans__user=request.user)
    pool = list(qs[:60])
    dates = random.sample(pool, min(3, len(pool)))
    wrappers = ["wrap-rose", "wrap-mint", "wrap-sky", "wrap-sun"]
    cards = [
        {
            "book": b,
            "fee": fee_for(b, via_blind_date=True),
            "wrapper": wrappers[i % len(wrappers)],
            "length": "a quick read" if b.pages and b.pages < 250 else "a long weekend" if b.pages < 450 else "an epic",
            "hints": [t.strip() for t in b.blind_date_teaser.split("·") if t.strip()],
        }
        for i, b in enumerate(dates)
    ]
    return render(request, "catalog/blind_date.html", {"cards": cards, "discount": int(float(policy("BLIND_DATE_DISCOUNT")) * 100)})


@login_required
@require_POST
def shelf_toggle(request, slug):
    book = get_object_or_404(Book, slug=slug)
    item, created = ShelfItem.objects.get_or_create(user=request.user, book=book)
    if not created:
        item.delete()
    if is_htmx(request):
        return render(request, "catalog/partials/shelf_button.html", {"book": book, "on_shelf": created})
    messages.success(request, "Added to your shelf." if created else "Removed from your shelf.")
    return redirect(request.POST.get("next") or book.get_absolute_url())


@login_required
@require_POST
def review_submit(request, slug):
    book = get_object_or_404(Book, slug=slug)
    loans = book.loans.filter(user=request.user)
    if not loans.exists():
        messages.error(request, "Only readers who borrowed this book can review it.")
        return redirect(book)
    existing = Review.objects.filter(book=book, user=request.user).first()
    form = ReviewForm(request.POST, instance=existing, blind_date=loans.filter(via_blind_date=True).exists())
    if form.is_valid():
        review = form.save(commit=False)
        review.book, review.user = book, request.user
        review.save()
        if not existing:
            from accounts.achievements import evaluate_badges
            from accounts.services import add_xp

            add_xp(request.user, 20)
            evaluate_badges(request.user)
        messages.success(request, "Thanks! Your review is live." if not existing else "Review updated.")
    else:
        messages.error(request, "Please add a star rating and a few words.")
    return redirect(book.get_absolute_url() + "#reviews")
