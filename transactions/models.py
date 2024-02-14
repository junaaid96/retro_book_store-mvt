from django.db import models
from users.models import UserAccount
from books.models import Book

# Create your models here.


class Transaction(models.Model):
    user = models.ForeignKey(
        UserAccount, related_name='transactions', on_delete=models.CASCADE)
    borrowed_book = models.ForeignKey(
        Book, related_name='transactions', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after_transaction = models.DecimalField(
        max_digits=10, decimal_places=2)
    borrow_timestamp = models.DateTimeField(auto_now_add=True)
    return_timestamp = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.user.username} - {self.amount} - {self.borrow_timestamp}"
