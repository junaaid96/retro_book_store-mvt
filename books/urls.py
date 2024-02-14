from django.urls import path
from .views import BookDetailsView, BorrowBookView, ReturnBookView

urlpatterns = [
    path('details/<int:pk>/', BookDetailsView.as_view(), name='book_details'),
    path('borrow/<int:pk>/', BorrowBookView.as_view(), name='borrow_book'),
    path('return/<int:transaction_id>/', ReturnBookView.as_view(), name='return_book'),
]
