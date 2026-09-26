from decimal import Decimal

from django import template
from django.conf import settings

register = template.Library()


@register.filter
def money(value):
    if value in (None, ""):
        value = 0
    value = Decimal(value)
    sign = "−" if value < 0 else ""
    return f"{sign}{settings.LIBRARY['CURRENCY']}{abs(value):,.2f}"


@register.filter
def stars(rating):
    """Return 5 items: 'full', 'half' or 'empty' for rendering star icons."""
    rating = float(rating or 0)
    out = []
    for i in range(1, 6):
        if rating >= i - 0.25:
            out.append("full")
        elif rating >= i - 0.75:
            out.append("half")
        else:
            out.append("empty")
    return out


@register.inclusion_tag("partials/cover.html")
def cover(book, size="md", extra=""):
    return {"book": book, "size": size, "extra": extra}


@register.inclusion_tag("partials/book_card.html", takes_context=True)
def book_card(context, book, compact=False):
    return {"book": book, "compact": compact, "request": context.get("request")}


@register.filter
def percent(value, total):
    try:
        return min(100, round(float(value) / float(total) * 100))
    except (TypeError, ZeroDivisionError, ValueError):
        return 0
