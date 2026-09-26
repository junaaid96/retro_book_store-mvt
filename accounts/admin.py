from django.contrib import admin

from .models import Notification, Profile, Transaction, UserBadge


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "balance", "xp", "reading_goal", "created_at"]
    search_fields = ["user__username", "user__email"]
    readonly_fields = ["balance"]
    filter_horizontal = ["favorite_genres"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["user", "kind", "amount", "balance_after", "note", "created_at"]
    list_filter = ["kind"]
    search_fields = ["user__username", "note"]

    def has_change_permission(self, request, obj=None):
        return False  # the ledger is append-only


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["user", "kind", "title", "is_read", "created_at"]
    list_filter = ["kind", "is_read"]


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ["user", "code", "awarded_at"]
    list_filter = ["code"]
