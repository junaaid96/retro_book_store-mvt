from django.db import models
from books.models import Book
from users.models import UserAccount
# Create your models here.


class Reviews(models.Model):
    borrowed_book = models.ForeignKey(
        Book, related_name='reviews', on_delete=models.CASCADE)
    reviewer = models.ForeignKey(
        UserAccount, related_name='reviews', on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
