# RetroBookStore — borrow stories, not shelves

A neighbourhood lending library, reimagined. Django 5.2 (MVT) + Neon serverless Postgres, with a warm retro design, dark mode, and discovery features borrowed from the best of modern library and reading apps.

Live: https://retro-book-store.onrender.com

## What's new in v3

| Feature | What it does |
| --- | --- |
| 🎭 **Mood-based discovery** | Pick how you want to *feel* (adventurous, cosy, tense…) plus a pace; books are ranked by how many of your moods they hit. Inspired by StoryGraph. |
| 💌 **Blind Date with a Book** | Three "wrapped" books shown only by spoiler-free hints. Borrow one at 20% off, unwrap it with a reveal animation, and rate the *chemistry* afterwards. Based on the popular library programme. |
| ⏳ **Waitlist / holds** | When every copy is out, join a queue. On return the next reader's copy is reserved for 48h and they get notified (in-app + email). Stale holds expire and pass down the line. |
| 📅 **Real circulation rules** | 14-day loans, up to 2 renewals (blocked if others are waiting), 5 books at once, per-day late fees, 50% refund on return. All money/stock changes run in one DB transaction with row locks. |
| 🔎 **Smart search** | Postgres full-text search (weighted title/author/genre/description, GIN index) + `pg_trgm` typo tolerance ("hobit" → The Hobbit), live results as you type, and a ⌘K / Ctrl+K quick-search palette. |
| ✨ **Recommendations** | "For you" (taste profile from loans, ratings, shelf and favourite genres), "Readers who borrowed this also borrowed…", and "If you like this, try…". |
| ⭐ **Verified reviews** | 1–5 star ratings with distribution bars; only people who borrowed a book can review it; spoiler blur. |
| 🏅 **Gamification** | XP & levels (Page Turner → Librarian of Legend), 10 badges, monthly borrow streaks, yearly reading goal ring, community leaderboard. |
| 🎁 **Reading Wrapped** | A Spotify-Wrapped-style yearly recap: books, pages, top genres & moods, favourite author, month-by-month chart and your *reader persona*. |
| 💰 **Wallet ledger** | Append-only transaction history with running balance, quick top-ups, filters. |
| 🔔 **Notifications** | Bell menu + inbox for holds ready, due soon, overdue, badges and deposits; optional emails. |
| 🛠️ **Staff dashboard** | KPIs, 30-day loan chart, overdue list, most borrowed, and a "buy more copies?" list ranked by waitlist per copy. |
| 🎨 **UI/UX** | Tailwind v4 design system, light/dark themes, generated fallback covers, Open Library cover art by ISBN, HTMX partial updates, responsive, keyboard- and screen-reader-friendly. |

## Architecture

```
accounts/     Profile (wallet, XP, goal), Transaction ledger, Notification, badges & achievements
catalog/      Genre, Mood, Author, Book (search vector), Review, ShelfItem; search & recommendations
circulation/  Loan, Hold and services.py — every borrowing rule lives here
core/         Staff dashboard, template tags, seed + cron management commands
templates/    Base layout and shared partials
assets/       Tailwind source (compiled to static/css/app.css)
```

Library policy (loan days, fees, limits…) lives in `settings.LIBRARY`.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set DATABASE_URL to your Neon connection string
python manage.py migrate
python manage.py seed_library --demo   # 48 books + demo readers, loans and reviews
python manage.py createsuperuser
python manage.py runserver
```

Front-end (only needed when you change templates/styles — the compiled CSS is committed):

```bash
npm install
npm run build        # vendors htmx/alpine/chart.js and compiles Tailwind
npm run watch:css    # while developing
```

Tests: `python manage.py test` (needs a Postgres the role can create a test DB on).

## Deploy (Vercel + Neon)

Live: https://retro-book-store.vercel.app — every push to `main` deploys to production.

- **Hosting:** Vercel's Django runtime (functions in `sin1`, next to the Neon database). Vercel runs `collectstatic` itself and serves `/static/` from its CDN.
- **Migrations:** `vercel.json` runs `python manage.py migrate` on production builds only (previews share the database, so they just run `check`).
- **Media uploads:** book covers go to the public `retro-media` bucket in Neon Object Storage via `django-storages` (S3 API).
- **Scheduled job:** Vercel Cron calls `/cron/circulation-sweep/` daily (Hobby plan limit) to expire holds and send due/overdue reminders. Any other scheduler can call it too with the header `Authorization: Bearer $CRON_SECRET`.

Environment variables (Vercel → Project → Settings → Environment Variables):

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Neon pooled connection string |
| `SECRET_KEY`, `DEBUG=False` | Django |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | `.vercel.app` / `https://*.vercel.app` |
| `AWS_ENDPOINT_URL_S3`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME` | Neon Object Storage credential + bucket |
| `CRON_SECRET` | Protects the cron endpoint |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Optional SMTP |

## Tech

Python 3.12 · Django 5.2 LTS · PostgreSQL 17 on Neon (full-text search, pg_trgm) · Tailwind CSS 4 · HTMX 2 · Alpine.js 3 · Chart.js 4 · WhiteNoise · django-storages · Vercel
