from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib.auth.models import User
from retro_book_store.constants import GENDER_TYPE
from .models import UserAccount


class UserRegistrationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=50, widget=forms.TextInput(attrs={'required': True}))
    last_name = forms.CharField(
        max_length=50, widget=forms.TextInput(attrs={'required': True}))
    email = forms.EmailField(
        max_length=100, widget=forms.TextInput(attrs={'required': True}))
    gender = forms.ChoiceField(choices=GENDER_TYPE)
    address = forms.CharField(max_length=100)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name',
                  'email', 'password1', 'password2', 'gender', 'address']

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()

            gender = self.cleaned_data.get('gender')
            address = self.cleaned_data.get('address')

            UserAccount.objects.create(
                user=user,
                gender=gender,
                address=address
            )

        return user

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': (
                    'appearance-none block w-full bg-gray-100 border border-gray-300 rounded py-2 px-4 leading-tight focus:outline-none focus:bg-white focus:border-gray-500'
                )
            })


class UserProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=50, widget=forms.TextInput(attrs={'required': True}))
    last_name = forms.CharField(
        max_length=50, widget=forms.TextInput(attrs={'required': True}))
    email = forms.EmailField(
        max_length=100, widget=forms.TextInput(attrs={'required': True}))
    
    gender = forms.ChoiceField(choices=GENDER_TYPE)
    address = forms.CharField(max_length=100)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': (
                    'appearance-none block w-full bg-gray-100 border border-gray-300 rounded py-2 px-4 leading-tight focus:outline-none focus:bg-white focus:border-gray-500'
                )
            })
            
        if self.instance:
            try:
                user_account = self.instance.account
            except UserAccount.DoesNotExist:
                user_account = None

            if user_account:
                self.fields['gender'].initial = user_account.gender
                self.fields['address'].initial = user_account.address

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()

            user_account, created = UserAccount.objects.get_or_create(
                user=user)

            user_account.gender = self.cleaned_data.get('gender')
            user_account.address = self.cleaned_data.get('address')
            user_account.save()

        return user
