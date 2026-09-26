from decimal import Decimal

from django.conf import settings


def site(request):
    context = {
        "CURRENCY": settings.LIBRARY["CURRENCY"],
        "LIBRARY": settings.LIBRARY,
        "BLIND_DISCOUNT": int(Decimal(settings.LIBRARY["BLIND_DATE_DISCOUNT"]) * 100),
        "REFUND_PERCENT": int(Decimal(settings.LIBRARY["RETURN_REFUND_RATE"]) * 100),
    }
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        context["unread_count"] = user.notifications.filter(is_read=False).count()
        context["nav_notifications"] = user.notifications.all()[:6]
    return context
