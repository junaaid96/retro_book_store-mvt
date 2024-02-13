from django.db import models
from django.contrib.auth.models import User
from retro_book_store.constants import GENDER_TYPE

# Create your models here.


class UserAccount(models.Model):
    # using the default User model and extending it with a OneToOneField
    user = models.OneToOneField(
        User, related_name='account', on_delete=models.CASCADE)
    # Adding more fields to the User model
    balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    gender = models.CharField(
        max_length=10, choices=GENDER_TYPE)
    address = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.user.username} - {self.balance}"
