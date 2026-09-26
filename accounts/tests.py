from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class RegistrationTests(TestCase):
    def test_duplicate_username_shows_a_form_error(self):
        User.objects.create_user(username="junaid", email="junaid@example.com", password="existing-password")

        response = self.client.post(
            reverse("register"),
            {
                "first_name": "New",
                "last_name": "Reader",
                "username": "junaid",
                "email": "new-reader@example.com",
                "password1": "strong-password-123",
                "password2": "strong-password-123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username="junaid").count(), 1)
        self.assertContains(response, "That username is already in use. Please choose another.")
