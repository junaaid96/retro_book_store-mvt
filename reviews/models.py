from django.db import models
from books.models import Book
from users.models import User
# Create your models here.


class Reviews(models.Model):
    book = models.ForeignKey(
        Book, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(
        User, related_name='reviews', on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
