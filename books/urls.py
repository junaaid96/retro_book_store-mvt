from django.urls import path
from .views import BookDetailsView

urlpatterns = [
    path('details/<int:pk>/', BookDetailsView.as_view(), name='book_details'),
]
