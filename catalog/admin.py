from django.contrib import admin

from .models import Author, Book, Genre, Mood, Review, ShelfItem


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ["name", "emoji", "slug"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Mood)
class MoodAdmin(admin.ModelAdmin):
    list_display = ["name", "emoji", "slug"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "borrowing_fee", "total_copies", "pace", "is_featured"]
    list_filter = ["genres", "moods", "pace", "is_featured"]
    list_editable = ["total_copies", "is_featured"]
    search_fields = ["title", "author__name", "isbn"]
    autocomplete_fields = ["author"]
    filter_horizontal = ["genres", "moods"]
    prepopulated_fields = {"slug": ["title"]}
    fieldsets = [
        (None, {"fields": ["title", "slug", "author", "description", "genres", "moods", "pace"]}),
        ("Cover", {"fields": ["isbn", "cover", "cover_url"]}),
        ("Details", {"fields": ["pages", "published_year", "language"]}),
        ("Lending", {"fields": ["borrowing_fee", "total_copies", "is_featured", "blind_date_teaser"]}),
    ]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["book", "user", "rating", "chemistry", "created_at"]
    list_filter = ["rating", "chemistry"]
    search_fields = ["book__title", "user__username", "body"]


admin.site.register(ShelfItem)
