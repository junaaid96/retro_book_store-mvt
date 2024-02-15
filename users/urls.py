from django.urls import path
from . import views
from borrowing_histories.views import HistoriesListView
from transactions.views import TransactionsListView, DepositMoneyView

urlpatterns = [
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogout.as_view(), name='logout'),
    path('profile/update/', views.UserProfileUpdateView.as_view(),
         name='profile_update'),

    path('profile/', HistoriesListView.as_view(), name='profile'),
    path('profile/transactions/',
         TransactionsListView.as_view(), name='transactions'),
    path('profile/deposit/', DepositMoneyView.as_view(), name='deposit'),
]
