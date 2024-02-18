from decimal import Decimal
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView
from .models import Book
from reviews.forms import ReviewForm
from users.models import UserAccount
from borrowing_histories.models import BorrowingHistory
from transactions.models import Transaction
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.views import View
from transactions.views import send_transaction_email

# Create your views here.


class BookDetailsView(LoginRequiredMixin, DetailView):
    model = Book
    template_name = 'book_details.html'

    def post(self, request, pk):
        user_account = UserAccount.objects.get(user=self.request.user)
        book = Book.objects.get(pk=pk)
        review_form = ReviewForm(request.POST)

        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.reviewer = user_account
            review.borrowed_book = book
            review.save()

            messages.success(request, 'Review added successfully!')
            return redirect('book_details', pk=book.pk)
        else:
            messages.error(request, 'Invalid review!')
            return redirect('book_details', pk=book.pk)

    def get_context_data(self, **kwargs):
        user_account = UserAccount.objects.get(user=self.request.user)
        context = super().get_context_data(**kwargs)
        book = Book.objects.get(pk=self.kwargs['pk'])
        reviews = book.reviews.all()
        context['user_account'] = user_account
        context['review_form'] = ReviewForm()
        context['reviews'] = reviews
        return context


class BorrowBookView(LoginRequiredMixin, CreateView):
    model = BorrowingHistory
    template_name = 'book_details.html'
    fields = []

    def form_valid(self, form):
        user_account = UserAccount.objects.get(user=self.request.user)
        book = Book.objects.get(pk=self.kwargs['pk'])

        if user_account.balance < book.borrowing_price:
            messages.error(
                self.request, 'Insufficient balance! Please deposit some money to your account.')
            return redirect('book_details', pk=book.pk)

        if book.total_copies == 0:
            messages.error(self.request, 'No available copies of this book!')
            return redirect('book_details', pk=book.pk)

        form.instance.borrower = user_account
        form.instance.borrowed_book = book
        form.instance.amount = book.borrowing_price

        user_account.balance -= book.borrowing_price
        user_account.save()

        book.borrowed_by.add(user_account)
        book.total_copies -= 1
        book.save()

        transaction = Transaction.objects.create(
            user=user_account, transaction_type='Borrow', amount=book.borrowing_price, balance_after_transaction=user_account.balance)
        transaction.save()

        return super().form_valid(form)

    def get_success_url(self):
        messages.success(self.request, 'Book borrowed successfully!')
        send_transaction_email(self.request.user, self.object.borrowed_book, self.request.user.email,
                               self.object.amount, 'Book Borrowed', 'email/borrow_email.html')
        return reverse_lazy('profile')


class ReturnBookView(LoginRequiredMixin, View):
    def post(self, request, history_id):
        user_account = UserAccount.objects.get(user=request.user)
        history = get_object_or_404(BorrowingHistory, id=history_id)
        book = history.borrowed_book

        returned_amount = book.borrowing_price * Decimal(0.5)

        user_account.balance += returned_amount
        user_account.save()

        history.return_timestamp = timezone.now()
        history.save()

        book.borrowed_by.remove(user_account)
        book.total_copies += 1
        book.save()

        transaction = Transaction.objects.create(
            user=user_account, transaction_type='Return', amount=returned_amount, balance_after_transaction=user_account.balance)
        transaction.save()

        messages.success(request, 'Book returned successfully!')
        send_transaction_email(request.user, history.borrowed_book, request.user.email,
                               returned_amount, 'Book Returned', 'email/return_email.html')
        return redirect('profile')
