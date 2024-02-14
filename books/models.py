from django.db import models
from users.models import UserAccount
from categories.models import Category
# Create your models here.


class Book(models.Model):
    title = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    description = models.TextField()
    borrowing_price = models.DecimalField(max_digits=10, decimal_places=2)
    cover = models.ImageField(upload_to='books/media/uploads/', blank=True)
    category = models.ManyToManyField(Category)
    total_copies = models.IntegerField(default=1)
    review = models.TextField(blank=True, null=True)
    borrowed_by = models.ManyToManyField(UserAccount, related_name='borrowed_books', blank=True)

    def __str__(self):
        return f"{self.title} - {self.author} - {self.borrowing_price}"
