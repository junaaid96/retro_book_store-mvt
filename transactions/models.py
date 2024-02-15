from django.db import models
from users.models import UserAccount
from retro_book_store.constants import TRANSACTION_TYPE

# Create your models here.


class Transaction(models.Model):
    user = models.ForeignKey(
        UserAccount, related_name='transaction', on_delete=models.CASCADE)
    transaction_type = models.CharField(
        max_length=10, choices=TRANSACTION_TYPE, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after_transaction = models.DecimalField(
        max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.user.user.username} - {self.transaction_type} - {self.amount}"
    
    class Meta:
        ordering = ['-timestamp']
