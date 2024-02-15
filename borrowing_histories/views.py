from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from borrowing_histories.models import BorrowingHistory
from users.models import UserAccount

# Create your views here.


class HistoriesListView(LoginRequiredMixin, ListView):
    model = BorrowingHistory
    template_name = 'profile.html'
    context_object_name = 'histories'

    def get_queryset(self):
        user_account = UserAccount.objects.get(user=self.request.user)
        histories_list = BorrowingHistory.objects.filter(borrower=user_account)
        return histories_list
