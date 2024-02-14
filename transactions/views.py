from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from .models import Transaction
from users.models import UserAccount

# Create your views here.

class TransactionsListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'transactions.html'
    context_object_name = 'transactions'

    def get_queryset(self):
        user_account = UserAccount.objects.get(user=self.request.user)
        transactions_list = Transaction.objects.filter(user=user_account)
        return transactions_list
    
    def get_context_data(self, **kwargs):
        user_account = UserAccount.objects.get(user=self.request.user)
        context = super().get_context_data(**kwargs)
        context['user_account'] = user_account
        return context