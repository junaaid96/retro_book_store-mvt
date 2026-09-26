from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "catalog"

    def ready(self):
        from django.db.models.signals import m2m_changed

        from .models import Book

        def refresh(sender, instance, action, **kwargs):
            if action in ("post_add", "post_remove", "post_clear") and isinstance(instance, Book):
                instance.refresh_search_vector()

        m2m_changed.connect(refresh, sender=Book.genres.through, dispatch_uid="book_genres_search")
