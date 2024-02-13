from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, ListView
from .models import Book
from users.models import UserAccount


# Create your views here.

class BookDetailsView(LoginRequiredMixin, DetailView):
    model = Book
    template_name = 'book_details.html'


class BooksListView(LoginRequiredMixin, ListView):
    model = Book
    template_name = 'profile.html'
    context_object_name = 'books'

    def get_queryset(self):
        # get the user account because i use custom user model
        user_account = UserAccount.objects.get(user=self.request.user)
        book_list = Book.objects.filter(borrowed_by=user_account)
        print(book_list)
        return book_list

