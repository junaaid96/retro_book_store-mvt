from django.urls import path
from . import views
from books.views import BooksListView

urlpatterns = [
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogout.as_view(), name='logout'),
    path('profile/update/', views.UserProfileUpdateView.as_view(),
         name='profile_update'),
    path('profile/', BooksListView.as_view(), name='profile'),
]
