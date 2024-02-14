from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, ListView
from .models import Book
from users.models import UserAccount


# Create your views here.

class BookDetailsView(LoginRequiredMixin, DetailView):
    model = Book
    template_name = 'book_details.html'

    def get_context_data(self, **kwargs):
        user_account = UserAccount.objects.get(user=self.request.user)
        context = super().get_context_data(**kwargs)
        context['user_account'] = user_account
        return context


class BooksListView(LoginRequiredMixin, ListView):
    model = Book
    template_name = 'profile.html'
    context_object_name = 'books'

    def get_queryset(self):
        # getting the user account because i've used custom user model
        user_account = UserAccount.objects.get(user=self.request.user)
        book_list = Book.objects.filter(borrowed_by=user_account)
        return book_list

