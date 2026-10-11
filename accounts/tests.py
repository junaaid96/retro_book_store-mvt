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


class DemoAccountTests(TestCase):
    def setUp(self):
        from django.core.management import call_command
        from catalog.models import Book
        if not Book.objects.exists():
            call_command("seed_library", verbosity=0)
        call_command("seed_demo", verbosity=0)
        call_command("seed_demo", verbosity=0)  # idempotent

    def test_login_page_shows_demo_card(self):
        r = self.client.get("/login/")
        self.assertContains(r, "Explore the demo")
        self.assertContains(r, "demo_librarian")

    def test_demo_users_can_log_in_with_roles(self):
        from django.contrib.auth.models import User
        from accounts.demo import DEMO_PASSWORD
        self.assertTrue(User.objects.get(username="demo_librarian").is_staff)
        self.assertFalse(User.objects.get(username="demo_librarian").is_superuser)
        self.assertTrue(self.client.login(username="demo_reader", password=DEMO_PASSWORD))
        self.assertTrue(User.objects.get(username="demo_reader").loans.exists())

    def test_demo_email_cannot_change(self):
        from django.contrib.auth.models import User
        from accounts.demo import DEMO_PASSWORD
        self.client.login(username="demo_reader", password=DEMO_PASSWORD)
        self.client.post("/account/settings/", {"u-first_name": "X", "u-last_name": "Y", "u-email": "evil@x.com", "p-reading_goal": 12})
        self.assertEqual(User.objects.get(username="demo_reader").email, "demo_reader@demo.retrobookstore")
