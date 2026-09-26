from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Notification, Transaction
from accounts.services import deposit
from catalog.models import Author, Book, Genre, Mood
from circulation import services
from circulation.models import Hold, Loan
from circulation.services import CirculationError


def make_user(name, balance="20"):
    user = User.objects.create_user(name, f"{name}@example.com", "pw-12345-long")
    if Decimal(balance):
        deposit(user, Decimal(balance))
    return user


def make_book(title="Dune", copies=1, fee="4.00", teaser="desert · spice"):
    author, _ = Author.objects.get_or_create(name="Frank Herbert")
    book = Book.objects.create(title=title, author=author, description="Sand.", borrowing_fee=Decimal(fee),
                               total_copies=copies, pages=600, blind_date_teaser=teaser)
    genre, _ = Genre.objects.get_or_create(name="Science Fiction", slug="science-fiction")
    mood, _ = Mood.objects.get_or_create(name="Adventurous", slug="adventurous")
    book.genres.add(genre)
    book.moods.add(mood)
    return book


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class BorrowReturnTests(TestCase):
    def setUp(self):
        self.reader = make_user("reader")
        self.book = make_book(copies=1)

    def test_borrow_charges_fee_and_creates_loan(self):
        loan = services.borrow(self.reader, self.book)
        self.reader.profile.refresh_from_db()
        self.assertEqual(self.reader.profile.balance, Decimal("16.00"))
        self.assertEqual(loan.fee_paid, Decimal("4.00"))
        self.assertEqual((loan.due_at - loan.borrowed_at).days, 14)
        self.assertTrue(Transaction.objects.filter(user=self.reader, kind="borrow", amount=Decimal("-4.00")).exists())
        self.assertTrue(self.reader.badges.filter(code="first_chapter").exists())

    def test_cannot_borrow_without_funds(self):
        poor = make_user("poor", balance="1")
        with self.assertRaises(CirculationError) as ctx:
            services.borrow(poor, self.book)
        self.assertEqual(ctx.exception.code, "funds")
        self.assertFalse(Loan.objects.exists())

    def test_cannot_borrow_twice_or_when_all_out(self):
        services.borrow(self.reader, self.book)
        with self.assertRaises(CirculationError):
            services.borrow(self.reader, self.book)
        other = make_user("other")
        with self.assertRaises(CirculationError) as ctx:
            services.borrow(other, self.book)
        self.assertEqual(ctx.exception.code, "unavailable")

    def test_on_time_return_refunds_half(self):
        loan = services.borrow(self.reader, self.book)
        loan = services.return_loan(self.reader, loan.pk)
        self.reader.profile.refresh_from_db()
        self.assertEqual(loan.refund, Decimal("2.00"))
        self.assertEqual(loan.late_fee, Decimal("0"))
        self.assertEqual(self.reader.profile.balance, Decimal("18.00"))

    def test_late_return_charges_per_day(self):
        loan = services.borrow(self.reader, self.book)
        Loan.objects.filter(pk=loan.pk).update(due_at=timezone.now() - timedelta(days=3))
        loan = services.return_loan(self.reader, loan.pk)
        self.assertEqual(loan.late_fee, Decimal("1.50"))
        self.reader.profile.refresh_from_db()
        self.assertEqual(self.reader.profile.balance, Decimal("16.50"))  # 20 - 4 + 2 - 1.5

    def test_return_is_idempotent(self):
        loan = services.borrow(self.reader, self.book)
        services.return_loan(self.reader, loan.pk)
        with self.assertRaises(CirculationError):
            services.return_loan(self.reader, loan.pk)

    def test_overdue_blocks_new_borrows_and_renewals(self):
        loan = services.borrow(self.reader, self.book)
        Loan.objects.filter(pk=loan.pk).update(due_at=timezone.now() - timedelta(hours=1))
        with self.assertRaises(CirculationError):
            services.renew(self.reader, loan.pk)
        with self.assertRaises(CirculationError) as ctx:
            services.borrow(self.reader, make_book("Other book", copies=2))
        self.assertEqual(ctx.exception.code, "overdue")

    def test_renew_extends_due_date_until_limit(self):
        loan = services.borrow(self.reader, self.book)
        due = loan.due_at
        loan = services.renew(self.reader, loan.pk)
        self.assertEqual(loan.due_at, due + timedelta(days=7))
        services.renew(self.reader, loan.pk)
        with self.assertRaises(CirculationError):
            services.renew(self.reader, loan.pk)

    def test_blind_date_discount(self):
        loan = services.borrow(self.reader, self.book, via_blind_date=True)
        self.assertEqual(loan.fee_paid, Decimal("3.20"))
        self.assertTrue(self.reader.badges.filter(code="blind_dater").exists())


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class WaitlistTests(TestCase):
    def setUp(self):
        self.book = make_book(copies=1)
        self.a, self.b, self.c = make_user("alice"), make_user("bob"), make_user("carol")
        self.loan = services.borrow(self.a, self.book)

    def test_hold_only_when_unavailable(self):
        free_book = make_book("Free", copies=3)
        with self.assertRaises(CirculationError) as ctx:
            services.place_hold(self.b, free_book)
        self.assertEqual(ctx.exception.code, "available")

    def test_queue_order_and_reserved_copy(self):
        hb = services.place_hold(self.b, self.book)
        hc = services.place_hold(self.c, self.book)
        self.assertEqual((hb.position, hc.position), (1, 2))

        services.return_loan(self.a, self.loan.pk)
        hb.refresh_from_db()
        self.assertEqual(hb.status, Hold.Status.READY)
        self.assertTrue(Notification.objects.filter(user=self.b, kind="hold_ready").exists())

        # Carol can't jump the queue; Bob can borrow his reserved copy.
        with self.assertRaises(CirculationError):
            services.borrow(self.c, self.book)
        services.borrow(self.b, self.book)
        hb.refresh_from_db()
        self.assertEqual(hb.status, Hold.Status.FULFILLED)
        self.assertTrue(self.b.badges.filter(code="patient_reader").exists())

    def test_expired_pickup_passes_to_next_reader(self):
        hb = services.place_hold(self.b, self.book)
        hc = services.place_hold(self.c, self.book)
        services.return_loan(self.a, self.loan.pk)
        Hold.objects.filter(pk=hb.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
        services.sweep_holds()
        hb.refresh_from_db()
        hc.refresh_from_db()
        self.assertEqual(hb.status, Hold.Status.EXPIRED)
        self.assertEqual(hc.status, Hold.Status.READY)

    def test_cancelling_ready_hold_promotes_next(self):
        hb = services.place_hold(self.b, self.book)
        hc = services.place_hold(self.c, self.book)
        services.return_loan(self.a, self.loan.pk)
        services.cancel_hold(self.b, hb.pk)
        hc.refresh_from_db()
        self.assertEqual(hc.status, Hold.Status.READY)

    def test_waitlist_blocks_renewal(self):
        services.place_hold(self.b, self.book)
        with self.assertRaises(CirculationError) as ctx:
            services.renew(self.a, self.loan.pk)
        self.assertEqual(ctx.exception.code, "waitlist")

    def test_reminders_sent_once(self):
        Loan.objects.filter(pk=self.loan.pk).update(due_at=timezone.now() + timedelta(days=1))
        self.assertEqual(services.send_reminders(), 1)
        self.assertEqual(services.send_reminders(), 0)


class ViewTests(TestCase):
    def setUp(self):
        self.book = make_book(copies=2)
        self.user = make_user("viewer")
        self.client.force_login(self.user)

    def test_public_pages_render(self):
        self.client.logout()
        for name, args in [("home", []), ("browse", []), ("discover", []), ("blind_date", []),
                           ("leaderboard", []), ("book_detail", [self.book.slug]), ("login", []), ("register", [])]:
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200, name)

    def test_member_pages_render(self):
        for name in ["dashboard", "wallet", "settings", "shelf", "history", "notifications", "wrapped"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_staff_dashboard_requires_staff(self):
        self.assertEqual(self.client.get(reverse("staff_dashboard")).status_code, 302)

    def test_borrow_flow_via_http(self):
        response = self.client.post(reverse("borrow", args=[self.book.slug]))
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(Loan.objects.filter(user=self.user).count(), 1)

    def test_only_borrowers_can_review(self):
        url = reverse("review_submit", args=[self.book.slug])
        self.client.post(url, {"rating": 5, "body": "Great"})
        self.assertFalse(self.book.reviews.exists())
        services.borrow(self.user, self.book)
        self.client.post(url, {"rating": 5, "body": "Great"})
        self.assertEqual(self.book.reviews.get().rating, 5)

    def test_typo_tolerant_search(self):
        response = self.client.get(reverse("browse"), {"q": "frank herbet"})
        self.assertContains(response, "Dune")

    def test_htmx_returns_partial(self):
        response = self.client.get(reverse("browse"), {"q": "dune"}, HTTP_HX_REQUEST="true")
        self.assertNotContains(response, "<html")
        self.assertContains(response, "Dune")

    def test_wallet_deposit_and_safe_redirect(self):
        response = self.client.post(reverse("wallet") + "?next=//evil.example", {"amount": "10"})
        self.assertRedirects(response, reverse("wallet"))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.balance, Decimal("30.00"))
