from django.contrib import admin

from .models import Hold, Loan


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ["book", "user", "borrowed_at", "due_at", "returned_at", "renewals", "fee_paid", "late_fee"]
    list_filter = ["via_blind_date", ("returned_at", admin.EmptyFieldListFilter)]
    search_fields = ["book__title", "user__username"]
    date_hierarchy = "borrowed_at"
    raw_id_fields = ["book", "user"]


@admin.register(Hold)
class HoldAdmin(admin.ModelAdmin):
    list_display = ["book", "user", "status", "created_at", "expires_at"]
    list_filter = ["status"]
    search_fields = ["book__title", "user__username"]
    raw_id_fields = ["book", "user"]
