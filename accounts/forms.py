from decimal import Decimal

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from catalog.models import Genre

from .models import Profile


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50, required=False)
    email = forms.EmailField()
    favorite_genres = forms.ModelMultipleChoiceField(
        queryset=Genre.objects.all(), required=False, widget=forms.CheckboxSelectMultiple(attrs={"class": "sr-only"}),
        help_text="Pick a few — we'll tailor your recommendations.",
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.profile.favorite_genres.set(self.cleaned_data["favorite_genres"])
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username or email")

    def clean(self):
        name = self.cleaned_data.get("username", "")
        if "@" in name:
            match = User.objects.filter(email__iexact=name).first()
            if match:
                self.cleaned_data["username"] = match.username
        return super().clean()


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("That email is used by another account.")
        return email


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["bio", "address", "reading_goal", "favorite_genres", "email_notifications"]
        widgets = {"favorite_genres": forms.CheckboxSelectMultiple(attrs={"class": "sr-only"})}
        labels = {"reading_goal": "Books to finish this year", "email_notifications": "Email me about holds and due dates"}


class DepositForm(forms.Form):
    amount = forms.DecimalField(min_value=Decimal("1"), max_value=Decimal("10000"), decimal_places=2)
