from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from accounts import views as accounts
from catalog import views as catalog
from circulation import views as circulation
from core import views as core

admin.site.site_header = "RetroBookStore admin"
admin.site.site_title = "RetroBookStore"

urlpatterns = [
    path("admin/", admin.site.urls),
    # Catalogue & discovery
    path("", catalog.home, name="home"),
    path("browse/", catalog.browse, name="browse"),
    path("search/suggest/", catalog.suggest, name="suggest"),
    path("discover/", catalog.discover, name="discover"),
    path("blind-date/", catalog.blind_date, name="blind_date"),
    path("books/<slug:slug>/", catalog.book_detail, name="book_detail"),
    path("books/<slug:slug>/shelf/", catalog.shelf_toggle, name="shelf_toggle"),
    path("books/<slug:slug>/review/", catalog.review_submit, name="review_submit"),
    path("authors/<slug:slug>/", catalog.author_detail, name="author_detail"),
    # Circulation
    path("books/<slug:slug>/borrow/", circulation.borrow, name="borrow"),
    path("books/<slug:slug>/hold/", circulation.place_hold, name="place_hold"),
    path("blind-date/<int:book_id>/borrow/", circulation.blind_date_borrow, name="blind_date_borrow"),
    path("blind-date/reveal/<int:loan_id>/", circulation.blind_date_reveal, name="blind_date_reveal"),
    path("loans/<int:loan_id>/return/", circulation.return_book, name="return_book"),
    path("loans/<int:loan_id>/renew/", circulation.renew, name="renew"),
    path("holds/<int:hold_id>/cancel/", circulation.cancel_hold, name="cancel_hold"),
    # Accounts
    path("register/", accounts.register, name="register"),
    path("login/", accounts.RetroLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("account/", accounts.dashboard, name="dashboard"),
    path("account/wallet/", accounts.wallet, name="wallet"),
    path("account/settings/", accounts.settings_view, name="settings"),
    path("account/shelf/", accounts.shelf, name="shelf"),
    path("account/history/", accounts.history, name="history"),
    path("account/notifications/", accounts.notifications, name="notifications"),
    path("account/notifications/read/", accounts.notifications_read, name="notifications_read"),
    path("wrapped/", accounts.wrapped, name="wrapped"),
    path("wrapped/<int:year>/", accounts.wrapped, name="wrapped_year"),
    path("leaderboard/", accounts.leaderboard, name="leaderboard"),
    # Staff
    path("staff/", core.staff_dashboard, name="staff_dashboard"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
