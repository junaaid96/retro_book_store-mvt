from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from catalog.models import Book

from . import services
from .models import Loan
from .services import CirculationError


def _back(request, fallback):
    nxt = request.POST.get("next", "")
    return nxt if nxt.startswith("/") and not nxt.startswith("//") else fallback


@login_required
@require_POST
def borrow(request, slug):
    book = get_object_or_404(Book, slug=slug)
    try:
        loan = services.borrow(request.user, book)
    except CirculationError as e:
        messages.error(request, str(e))
        if e.code == "funds":
            return redirect(reverse("wallet") + f"?next={book.get_absolute_url()}")
        return redirect(book)
    messages.success(
        request, f"“{book.title}” is yours until {timezone.localtime(loan.due_at):%a %d %b}. Happy reading! 📚"
    )
    return redirect("dashboard")


@login_required
@require_POST
def blind_date_borrow(request, book_id):
    book = get_object_or_404(Book.objects.exclude(blind_date_teaser=""), pk=book_id)
    try:
        loan = services.borrow(request.user, book, via_blind_date=True)
    except CirculationError as e:
        messages.error(request, str(e))
        if e.code == "funds":
            return redirect(reverse("wallet") + f"?next={reverse('blind_date')}")
        return redirect("blind_date")
    return redirect("blind_date_reveal", loan_id=loan.pk)


@login_required
def blind_date_reveal(request, loan_id):
    loan = get_object_or_404(Loan.objects.select_related("book", "book__author"), pk=loan_id, user=request.user,
                             via_blind_date=True)
    xp = services.XP_BORROW + services.XP_BLIND_DATE
    return render(request, "circulation/reveal.html", {"loan": loan, "book": loan.book, "xp": xp})


@login_required
@require_POST
def return_book(request, loan_id):
    try:
        loan = services.return_loan(request.user, loan_id)
    except CirculationError as e:
        messages.error(request, str(e))
    else:
        parts = [f"Returned “{loan.book.title}”."]
        if loan.refund:
            parts.append(f"Refunded {services.policy('CURRENCY')}{loan.refund:,.2f}.")
        if loan.late_fee:
            parts.append(f"Late fee {services.policy('CURRENCY')}{loan.late_fee:,.2f}.")
        else:
            parts.append(f"+{services.XP_ON_TIME} XP for being on time ✨")
        messages.success(request, " ".join(parts))
        if not loan.book.reviews.filter(user=request.user).exists():
            messages.info(request, f"How was it? Leave a quick review of “{loan.book.title}” for +20 XP.")
    return redirect(_back(request, reverse("dashboard")))


@login_required
@require_POST
def renew(request, loan_id):
    try:
        loan = services.renew(request.user, loan_id)
    except CirculationError as e:
        messages.error(request, str(e))
    else:
        messages.success(request, f"Renewed! New due date: {timezone.localtime(loan.due_at):%a %d %b}.")
    return redirect(_back(request, reverse("dashboard")))


@login_required
@require_POST
def place_hold(request, slug):
    book = get_object_or_404(Book, slug=slug)
    try:
        hold = services.place_hold(request.user, book)
    except CirculationError as e:
        messages.error(request, str(e))
    else:
        messages.success(request, f"You're #{hold.position} on the waitlist. We'll notify you when it's your turn.")
    return redirect(book)


@login_required
@require_POST
def cancel_hold(request, hold_id):
    try:
        services.cancel_hold(request.user, hold_id)
    except CirculationError as e:
        messages.error(request, str(e))
    else:
        messages.success(request, "Hold cancelled.")
    return redirect(_back(request, reverse("dashboard")))
