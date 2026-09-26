from decimal import Decimal

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.text import slugify


class Genre(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True)
    emoji = models.CharField(max_length=8, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("browse") + f"?genre={self.slug}"


class Mood(models.Model):
    """How a book feels to read (StoryGraph-style), used for mood discovery."""

    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    emoji = models.CharField(max_length=8, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Author(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    bio = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("author_detail", args=[self.slug])


def _count_subquery(model, filters):
    return Coalesce(
        Subquery(
            model.objects.filter(book=OuterRef("pk"), **filters)
            .values("book")
            .annotate(c=Count("pk"))
            .values("c")[:1],
            output_field=IntegerField(),
        ),
        Value(0),
    )


class BookQuerySet(models.QuerySet):
    def with_stats(self):
        """Annotate availability, rating and popularity without row explosion."""
        from circulation.models import Hold, Loan

        rating = (
            Review.objects.filter(book=OuterRef("pk"))
            .values("book")
            .annotate(a=Avg("rating"))
            .values("a")[:1]
        )
        return self.annotate(
            active_loans=_count_subquery(Loan, {"returned_at__isnull": True}),
            reserved=_count_subquery(Hold, {"status": Hold.Status.READY}),
            waiting=_count_subquery(Hold, {"status": Hold.Status.WAITING}),
            times_borrowed=_count_subquery(Loan, {}),
            review_count=_count_subquery(Review, {}),
            avg_rating=Subquery(rating, output_field=models.FloatField()),
        )


class Book(models.Model):
    class Pace(models.TextChoices):
        SLOW = "slow", "Slow burn"
        MEDIUM = "medium", "Steady"
        FAST = "fast", "Page-turner"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    author = models.ForeignKey(Author, related_name="books", on_delete=models.PROTECT)
    description = models.TextField()
    isbn = models.CharField("ISBN-13", max_length=13, blank=True)
    cover = models.ImageField(upload_to="covers/", blank=True)
    cover_url = models.URLField(blank=True, help_text="Leave empty to use Open Library by ISBN.")
    pages = models.PositiveIntegerField(default=0)
    published_year = models.PositiveSmallIntegerField(null=True, blank=True)
    language = models.CharField(max_length=30, default="English")
    genres = models.ManyToManyField(Genre, related_name="books")
    moods = models.ManyToManyField(Mood, related_name="books", blank=True)
    pace = models.CharField(max_length=10, choices=Pace.choices, default=Pace.MEDIUM)
    borrowing_fee = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("3.00"))
    total_copies = models.PositiveSmallIntegerField(default=1)
    blind_date_teaser = models.CharField(
        max_length=160,
        blank=True,
        help_text="Spoiler-free hints shown on Blind Date cards, e.g. 'heist · found family · rainy city'.",
    )
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    search_vector = SearchVectorField(null=True, editable=False)

    objects = BookQuerySet.as_manager()

    class Meta:
        ordering = ["title"]
        indexes = [GinIndex(fields=["search_vector"], name="book_search_gin")]

    def __str__(self):
        return f"{self.title} — {self.author}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200] or "book"
            slug, n = base, 2
            while Book.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)
        self.refresh_search_vector()

    def refresh_search_vector(self):
        genres = " ".join(self.genres.values_list("name", flat=True)) if self.pk else ""
        Book.objects.filter(pk=self.pk).update(
            search_vector=(
                SearchVector(Value(self.title), weight="A", config="english")
                + SearchVector(Value(self.author.name), weight="A", config="english")
                + SearchVector(Value(genres), weight="B", config="english")
                + SearchVector(Value(self.blind_date_teaser), weight="C", config="english")
                + SearchVector(Value(self.description), weight="D", config="english")
            )
        )

    def get_absolute_url(self):
        return reverse("book_detail", args=[self.slug])

    @property
    def cover_src(self):
        if self.cover:
            return self.cover.url
        if self.cover_url:
            return self.cover_url
        if self.isbn:
            return f"https://covers.openlibrary.org/b/isbn/{self.isbn}-L.jpg?default=false"
        return ""

    @property
    def palette(self):
        """Deterministic colour pair for the generated fallback cover."""
        palettes = [
            ("#7c2d12", "#fed7aa"), ("#134e4a", "#99f6e4"), ("#1e3a8a", "#bfdbfe"),
            ("#581c87", "#e9d5ff"), ("#713f12", "#fde68a"), ("#831843", "#fbcfe8"),
            ("#14532d", "#bbf7d0"), ("#3f3f46", "#e4e4e7"),
        ]
        return palettes[(self.pk or 0) % len(palettes)]

    def available_copies(self):
        if hasattr(self, "active_loans"):
            return max(self.total_copies - self.active_loans - self.reserved, 0)
        from circulation.models import Hold

        loans = self.loans.filter(returned_at__isnull=True).count()
        ready = self.holds.filter(status=Hold.Status.READY).count()
        return max(self.total_copies - loans - ready, 0)


class Review(models.Model):
    class Chemistry(models.TextChoices):
        TRUE_LOVE = "true_love", "💘 True love"
        CRUSH = "crush", "😊 Strong crush"
        COMPLICATED = "complicated", "🤔 It's complicated"
        FRIEND_ZONE = "friend_zone", "🤝 Friend zone"
        NO_CHEMISTRY = "no_chemistry", "🧊 No chemistry"

    book = models.ForeignKey(Book, related_name="reviews", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="reviews", on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    body = models.TextField(max_length=2000)
    chemistry = models.CharField(max_length=20, choices=Chemistry.choices, blank=True)
    contains_spoilers = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["book", "user"], name="one_review_per_reader"),
            models.CheckConstraint(condition=Q(rating__gte=1, rating__lte=5), name="rating_1_to_5"),
        ]

    def __str__(self):
        return f"{self.user} on {self.book.title} ({self.rating}★)"


class ShelfItem(models.Model):
    """A book on a reader's 'Want to read' shelf."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="shelf", on_delete=models.CASCADE)
    book = models.ForeignKey(Book, related_name="shelved_by", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "book"], name="unique_shelf_item")]
