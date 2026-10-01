# Tanu

Marketplace for UMD students. V1: students list services (tutoring, photography, design, hair/beauty, etc.), customers book and pay through Tanu, and providers are paid out via Stripe Connect. V2 adds goods (buy/sell items, Facebook Marketplace style) and messaging.

Full architecture rationale and trade-offs: @docs/architecture-decisions.md (local only; `docs/` is gitignored).

## Repo layout (monorepo)

- `backend/` – Django + Django REST Framework. One service, one Postgres database. API-first.
  - `config/` – settings (`base`, `dev`, `test`, `prod`), URLs, WSGI/ASGI.
  - `apps/accounts` – custom `User` (email login, no username), UMD-email signup check.
  - `apps/listings` – service listings, categories, photos.
  - `apps/bookings` – availability, appointments, booking state machine.
  - `apps/payments` – Stripe Connect, ledger, webhooks.
  - `apps/reviews`, `apps/trust` (license verification, reports, moderation), `apps/notifications` (emails, background jobs).
- `web/` – Next.js + TypeScript. Currently a mock UI for exercising the API.
- `mobile/` – React Native (Expo), planned.
- `contracts/openapi.yaml` – generated from the backend. Never edit by hand; regenerate (see Commands). Web/mobile generate their TypeScript types from it.
- `docker-compose.yml` – local Postgres + backend.

## Commands

```bash
docker compose up --build                       # Postgres (host port 5433) + API at http://localhost:8000
docker compose exec backend pytest              # backend tests
docker compose exec backend python manage.py makemigrations
cd backend && uv run python manage.py spectacular --file ../contracts/openapi.yaml   # regenerate contract
cd web && npm run dev                           # web app at http://localhost:3000 (run natively, not in Docker)
```

API docs: http://localhost:8000/api/docs/. Health: `/api/health/`. Auth (django-allauth headless): `/api/auth/`.

## Hard rules

### Code organization
- Business rules and state changes live in each app's `services.py` (e.g. `bookings.services.confirm_booking()`). Views and serializers call services; they never set `status` fields or write ledger rows directly.
- Apps don't reach into another app's models to change them; call that app's services.
- External providers sit behind our own interface: Stripe only via `apps/payments/services.py`, email via Django mailers, files via Django storages, background jobs via Procrastinate tasks.

### API-first
- All features go through DRF JSON endpoints, because web and mobile share one API. Django templates only for admin.
- After changing endpoints or serializers, regenerate `contracts/openapi.yaml` in the same change. CI fails if it is stale.

### Accounts
- Signup is limited to verified UMD emails, `umd.edu` and `terpmail.umd.edu` (`TANU_ALLOWED_EMAIL_DOMAINS`); email verification is mandatory before login. Don't weaken this.

### Money and payments
- Money is integer cents with an explicit currency. Never floats.
- `apps/payments` is the only app that imports `stripe`. Stripe keys come from environment variables, never source control.
- The ledger is append-only, double-entry. Balances are derived from entries, never edited.
- A state change and its ledger entries commit in one `transaction.atomic()`.
- Background jobs that must only run if a transaction commits are enqueued inside that transaction (Procrastinate stores jobs in the same Postgres database).
- Webhooks: verify the Stripe signature, then store Stripe `event.id` under a unique constraint before handling. Duplicates are acknowledged and skipped.
- Pass Stripe idempotency keys on all outgoing writes (charges, transfers, refunds).
- Booking and payment status are state machines with explicit allowed transitions. Never overwrite state with whatever event arrived last.
- Services are paid on-platform (through Stripe). Goods (V2) are paid off-platform between buyer and seller.

### Product and compliance constraints
- Regulated categories (haircuts/barbering, nails, lashes, brows, esthetics) require a verified Maryland license number before a listing can go live. Unregulated categories need no license.
- Service locations must not include UMD residence halls. Allowed: provider's off-campus place, client's off-campus place, licensed shop, or remote.
- Tutoring listings may not offer completing graded work or exam answers.
- No UMD logos, Testudo, or "official UMD" wording. The footer states Tanu is independent and not affiliated with or endorsed by UMD.
- Store datetimes in UTC; display in America/New_York.

## CI
- `.github/workflows/ci.yml`, path-filtered: `backend/` changes run ruff, migration check, contract check, and pytest; `web/` changes run lint, type check, and build.
