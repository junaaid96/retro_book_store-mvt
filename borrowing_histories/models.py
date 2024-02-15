from django.db import models
from users.models import UserAccount
from books.models import Book

# Create your models here.


class BorrowingHistory(models.Model):
    borrower = models.ForeignKey(
        UserAccount, related_name='history', on_delete=models.CASCADE)
    borrowed_book = models.ForeignKey(
        Book, related_name='history', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    borrow_timestamp = models.DateTimeField(auto_now_add=True)
    return_timestamp = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.borrower.user.username} - {self.borrowed_book.title}"
