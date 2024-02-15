# from django.views.generic import CreateView, ListView
# from .models import Reviews
# from users.models import UserAccount
# from books.models import Book
# from reviews.forms import ReviewForm
# from django.urls import reverse_lazy

# # Create your views here.


# class ReviewCreateView(CreateView):
#     model = Reviews
#     template_name = 'book_details.html'
#     form_class = ReviewForm

#     def form_valid(self, form):
#         user = UserAccount.objects.get(user=self.request.user)
#         book = Book.objects.get(pk=self.kwargs['pk'])

#         form.instance.borrowed_book = book
#         form.instance.borrower = user

#         return super().form_valid(form)

#     def get_success_url(self):
#         return reverse_lazy('book_details', kwargs={'pk': self.kwargs['pk']})


# class ReviewsListView(ListView):
#     model = Reviews
#     template_name = 'reviews_list.html'
#     context_object_name = 'reviews'
#     paginate_by = 10

#     def get_queryset(self):
#         book = Book.objects.get(pk=self.kwargs['pk'])
#         return Reviews.objects.filter(borrowed_book=book).order_by('-created_at')
