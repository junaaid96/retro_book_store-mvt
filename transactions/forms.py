from django import forms
from .models import Transaction


class DepositMoneyForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['amount']
