from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, ExpressionWrapper, F, FloatField, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone

from accounts.models import Profile, Transaction
from catalog.models import Book
from circulation.models import Hold, Loan


@staff_member_required
def staff_dashboard(request):
    now = timezone.now()
    since = now - timedelta(days=29)
    daily = {
        row["day"]: row["n"]
        for row in Loan.objects.filter(borrowed_at__gte=since)
        .annotate(day=TruncDate("borrowed_at"))
        .values("day")
        .annotate(n=Count("pk"))
    }
    days = [(timezone.localdate() - timedelta(days=i)) for i in range(29, -1, -1)]
    money = Transaction.objects.aggregate(
        fees=Sum("amount", filter=Q(kind__in=["borrow", "late_fee"])),
        refunds=Sum("amount", filter=Q(kind="refund")),
        deposits=Sum("amount", filter=Q(kind="deposit")),
    )
    revenue = -(money["fees"] or 0) - (money["refunds"] or 0)

    books = Book.objects.with_stats().select_related("author")
    context = {
        "kpis": {
            "titles": Book.objects.count(),
            "copies": Book.objects.aggregate(n=Sum("total_copies"))["n"] or 0,
            "on_loan": Loan.objects.active().count(),
            "overdue": Loan.objects.overdue().count(),
            "members": Profile.objects.count(),
            "waitlist": Hold.objects.filter(status=Hold.Status.WAITING).count(),
            "revenue": revenue,
            "deposits": money["deposits"] or 0,
        },
        "overdue": Loan.objects.overdue().select_related("book", "user").order_by("due_at")[:15],
        "popular": books.order_by("-times_borrowed")[:8],
        "demand": books.filter(waiting__gt=0)
        .annotate(pressure=ExpressionWrapper(F("waiting") * 1.0 / F("total_copies"), output_field=FloatField()))
        .order_by("-pressure")[:8],
        "chart": {"labels": [d.strftime("%d %b") for d in days], "values": [daily.get(d, 0) for d in days]},
    }
    return render(request, "core/staff_dashboard.html", context)
