from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView
from .models import Book
from users.models import UserAccount
from transactions.models import Transaction
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.views import View

# Create your views here.


class BookDetailsView(LoginRequiredMixin, DetailView):
    model = Book
    template_name = 'book_details.html'

    def get_context_data(self, **kwargs):
        user_account = UserAccount.objects.get(user=self.request.user)
        context = super().get_context_data(**kwargs)
        context['user_account'] = user_account
        return context


# class BooksListView(LoginRequiredMixin, ListView):
#     model = Book
#     template_name = 'profile.html'
#     context_object_name = 'books'

#     def get_queryset(self):
#         # getting the user account because i've used custom user model
#         user_account = UserAccount.objects.get(user=self.request.user)
#         book_list = Book.objects.filter(borrowed_by=user_account)
#         return book_list


class BorrowBookView(LoginRequiredMixin, CreateView):
    model = Transaction
    template_name = 'book_details.html'
    fields = []

    def form_valid(self, form):
        user_account = UserAccount.objects.get(user=self.request.user)
        book = Book.objects.get(pk=self.kwargs['pk'])

        form.instance.user = user_account
        form.instance.borrowed_book = book
        form.instance.amount = book.borrowing_price
        form.instance.balance_after_transaction = user_account.balance - book.borrowing_price

        user_account.balance -= book.borrowing_price
        user_account.save()

        book.borrowed_by.add(user_account)
        book.total_copies -= 1
        book.save()

        return super().form_valid(form)

    def get_success_url(self):
        messages.success(self.request, 'Book borrowed successfully!')
        return reverse_lazy('profile')


class ReturnBookView(LoginRequiredMixin, View):
    def post(self, request, transaction_id):
        user_account = UserAccount.objects.get(user=request.user)
        transaction = get_object_or_404(Transaction, id=transaction_id)
        book = transaction.borrowed_book

        transaction.return_timestamp = timezone.now()
        transaction.save()

        book.borrowed_by.remove(user_account)
        book.total_copies += 1
        book.save()

        messages.success(request, 'Book returned successfully!')
        return redirect('profile')
