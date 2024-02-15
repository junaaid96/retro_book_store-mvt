from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, ListView
from .models import Transaction
from users.models import UserAccount
from .forms import DepositMoneyForm
from django.urls import reverse_lazy
from django.contrib import messages

# Create your views here.


class DepositMoneyView(LoginRequiredMixin, CreateView):
    model = Transaction
    template_name = 'deposit.html'
    form_class = DepositMoneyForm

    def form_valid(self, form):
        user_account = UserAccount.objects.get(user=self.request.user)

        form.instance.user = user_account
        form.instance.transaction_type = 'Deposit'
        form.instance.balance_after_transaction = user_account.balance + form.instance.amount

        user_account.balance += form.instance.amount
        user_account.save()
        return super().form_valid(form)

    # def get_form_kwargs(self):
    #     user_account = UserAccount.objects.get(user=self.request.user)
    #     kwargs = super().get_form_kwargs()
    #     kwargs['instance'] = Transaction(user=user_account)
    #     return kwargs

    def get_success_url(self):
        messages.success(self.request, 'Money deposited successfully')
        return reverse_lazy('transactions')


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
