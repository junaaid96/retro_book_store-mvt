"""Search, filtering and recommendation queries for the catalogue."""

from collections import Counter

from django.contrib.postgres.search import SearchQuery, SearchRank, TrigramWordSimilarity
from django.db.models import Count, F, FloatField, Q, Value
from django.db.models.functions import Coalesce, Greatest

from .models import Book

SORTS = {
    "relevance": "Best match",
    "popular": "Most borrowed",
    "rating": "Top rated",
    "newest": "Newest arrivals",
    "title": "Title A–Z",
    "fee": "Lowest fee",
}


def search_books(qs, q):
    """Full-text search with typo tolerance (pg_trgm) on title and author."""
    q = q.strip()
    if not q:
        return qs
    query = SearchQuery(q, search_type="websearch", config="english")
    return (
        qs.annotate(
            rank=Coalesce(SearchRank(F("search_vector"), query), Value(0.0), output_field=FloatField()),
            fuzzy=Greatest(
                TrigramWordSimilarity(q, "title"), TrigramWordSimilarity(q, "author__name")
            ),
        )
        .filter(
            Q(search_vector=query)
            | Q(fuzzy__gte=0.45)
            | Q(title__icontains=q)
            | Q(author__name__icontains=q)
            | Q(isbn=q.replace("-", ""))
        )
    )


def filter_books(params):
    qs = Book.objects.with_stats().select_related("author").prefetch_related("genres")
    q = params.get("q", "").strip()
    genres = [g for g in params.getlist("genre") if g]
    moods = [m for m in params.getlist("mood") if m]
    pace = params.get("pace", "")
    sort = params.get("sort") or ("relevance" if q else "popular")

    if q:
        qs = search_books(qs, q)
    if genres:
        qs = qs.filter(genres__slug__in=genres)
    for mood in moods:  # every selected mood must match
        qs = qs.filter(moods__slug=mood)
    if pace in Book.Pace.values:
        qs = qs.filter(pace=pace)
    if params.get("available"):
        qs = qs.filter(total_copies__gt=F("active_loans") + F("reserved"))
    if params.get("short"):
        qs = qs.filter(pages__gt=0, pages__lte=250)
    qs = qs.distinct()

    order = {
        "relevance": ["-rank", "-fuzzy", "title"] if q else ["-times_borrowed", "title"],
        "popular": ["-times_borrowed", "title"],
        "rating": [F("avg_rating").desc(nulls_last=True), "-review_count", "title"],
        "newest": ["-created_at"],
        "title": ["title"],
        "fee": ["borrowing_fee", "title"],
    }.get(sort, ["-times_borrowed", "title"])
    return qs.order_by(*order), sort


def similar_books(book, limit=6):
    """Books sharing the most genres and moods, same author first."""
    return (
        Book.objects.with_stats()
        .select_related("author")
        .exclude(pk=book.pk)
        .annotate(
            overlap=Count("genres", filter=Q(genres__in=book.genres.all()), distinct=True)
            + Count("moods", filter=Q(moods__in=book.moods.all()), distinct=True)
        )
        .filter(Q(overlap__gt=0) | Q(author=book.author_id))
        .order_by("-overlap", "-times_borrowed")[:limit]
    )


def also_borrowed(book, limit=6):
    """'Readers who borrowed this also borrowed…' via loan co-occurrence."""
    readers = book.loans.values("user")
    return (
        Book.objects.with_stats()
        .select_related("author")
        .exclude(pk=book.pk)
        .filter(loans__user__in=readers)
        .annotate(co=Count("loans__user", distinct=True))
        .order_by("-co", "title")[:limit]
    )


def taste_profile(user):
    """Weighted genre and mood affinity from loans, reviews, shelf and favourites."""
    genres, moods = Counter(), Counter()

    def add(books, weight):
        for g in Book.genres.through.objects.filter(book__in=books).values_list("genre_id", flat=True):
            genres[g] += weight
        for m in Book.moods.through.objects.filter(book__in=books).values_list("mood_id", flat=True):
            moods[m] += weight

    add(user.loans.values("book"), 2)
    add(user.reviews.filter(rating__gte=4).values("book"), 3)
    add(user.reviews.filter(rating__lte=2).values("book"), -3)
    add(user.shelf.values("book"), 1)
    for g in user.profile.favorite_genres.values_list("pk", flat=True):
        genres[g] += 4
    return genres, moods


def recommended_for(user, limit=8):
    """Score unread books by taste match, nudged by popularity and rating."""
    genres, moods = taste_profile(user)
    base = Book.objects.with_stats().select_related("author").exclude(loans__user=user)
    if not genres and not moods:
        return list(base.order_by("-times_borrowed", "-is_featured", "title")[:limit])

    candidates = list(base.prefetch_related("genres", "moods")[:300])
    scored = []
    for b in candidates:
        score = sum(genres[g.pk] for g in b.genres.all()) + 0.7 * sum(moods[m.pk] for m in b.moods.all())
        score += 0.3 * b.times_borrowed + (b.avg_rating or 0) * 0.5
        if score > 0:
            scored.append((score, b))
    scored.sort(key=lambda t: (-t[0], t[1].title))
    return [b for _, b in scored[:limit]]
