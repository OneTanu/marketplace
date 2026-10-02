# Tanu

Student-only marketplace for buying and selling items on campus, starting at UMD and expanding to other schools. Every user is a verified student, and each user and listing belongs to one school. V1 is items (payment happens off-platform between buyer and seller). V2 brings back services (tutoring, photography, etc.) with bookings and Stripe Connect.

Full architecture rationale and trade-offs: @docs/architecture-decisions.md (local only; `docs/` is gitignored).

## Repo layout (monorepo)

- `backend/` – Django + Django REST Framework. One service, one Postgres database. API-first.
  - `config/` – settings (`base`, `dev`, `test`, `prod`), URLs, WSGI/ASGI.
  - `apps/schools` – `School` and `SchoolDomain` (which email domains belong to which school).
  - `apps/accounts` – custom `User` (email login, no username, `school`), signup restricted to registered school domains.
  - `apps/listings` – `Listing` (shared fields) plus one-to-one `ItemDetails` / `ServiceDetails`, `Category`, `ListingPhoto`.
  - `apps/messaging` – conversations between buyers and sellers.
  - `apps/deals` – offers, Buy now, Pending/Sold, handoff confirmation.
  - `apps/reviews`, `apps/trust` (reports, blocking, moderation), `apps/notifications` (notifications, watched searches, emails).
  - `apps/bookings`, `apps/payments` – V2 (services), empty for now.
- `web/` – Next.js + TypeScript, responsive (mobile-first) and installable as a PWA. Proxies `/api` and `/media` to Django.
- `contracts/openapi.yaml` – generated from the backend. Never edit by hand. `web/src/lib/api/schema.d.ts` is generated from it.
- `docker-compose.yml` – local Postgres + backend.

## Commands

```bash
docker compose up --build                       # Postgres (host port 5433) + API at http://localhost:8000
docker compose exec backend pytest              # backend tests
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py createsuperuser   # then use /admin
cd backend && uv run python manage.py spectacular --file ../contracts/openapi.yaml   # regenerate contract
cd web && pnpm install                          # web dependencies (pnpm, not npm; one-time: npm install -g pnpm@12.8.1)
cd web && pnpm dev                              # web app at http://localhost:3000 (run natively, not in Docker)
cd web && pnpm api:types                        # regenerate TS types after the contract changes
cd web && pnpm typecheck                        # Next.js route types + tsc
```

API docs: http://localhost:8000/api/docs/. Health: `/api/health/`. Auth (django-allauth headless): `/api/auth/`. Admin: `/admin/`.

## Hard rules

### Tooling
- The web app uses **pnpm**, pinned in `web/package.json` (`packageManager`). Never run `npm install` in `web/` or commit a `package-lock.json`. Add packages with `pnpm add <pkg>` (`-D` for dev tools).
- pnpm blocks dependency install scripts unless listed under `allowBuilds` in `web/pnpm-workspace.yaml`. Approve one only when it's needed, with `pnpm approve-builds <pkg>`.
- The backend uses **uv** (`uv add`, `uv run`); `uv.lock` is committed.

### Code organization
- Business rules and state changes live in each app's `services.py` (e.g. `deals.services.accept_offer()`). Views and serializers call services; they never set `status` fields directly.
- Apps don't reach into another app's models to change them; call that app's services.
- External providers sit behind our own interface: email via Django mailers, files via Django storages, background jobs via Procrastinate tasks, and (V2) Stripe only via `apps/payments/services.py`.

### API-first
- All features go through DRF JSON endpoints, because web and mobile share one API. Django templates only for admin.
- After changing endpoints or serializers, regenerate `contracts/openapi.yaml` and `web/src/lib/api/schema.d.ts` in the same change. CI fails if either is stale.
- Our DRF URLs end in `/`, so call them with the slash (`/api/health/`). allauth's `/api/auth/...` URLs have no trailing slash.

### Schools and accounts
- Signup requires a verified email on a domain registered to an active `School` (UMD: `umd.edu`, `terpmail.umd.edu`). Email verification is mandatory before login. Don't weaken this.
- Adding a school is data (an admin or migration row), never code or settings.
- A user's school is set once at signup from their verified email; changing it is an admin action.
- A listing's `school` is always its seller's school. Feeds and searches filter by the viewer's school unless they explicitly widen the scope.

### Listings
- Shared fields go on `Listing`; kind-specific fields go on `ItemDetails` / `ServiceDetails`. Don't add item-only or service-only columns to `Listing`.
- Item status: Available → Pending (seller accepted a buyer) → Sold (both confirmed the handoff). Pending can return to Available. Removed is for sellers and moderation. Never mark Sold on a Buy now click.
- Timers: the seller has 24h to answer a request or offer; a Pending deal returns to Available after 72h without a confirmed handoff. Both run as background jobs.

### Data and money
- Money is integer cents with an explicit currency. Never floats.
- Every database change is a migration. Never change a database by hand, including production.
- Background jobs that must only run if a transaction commits are enqueued inside that transaction (Procrastinate stores jobs in the same Postgres database).
- V2 payments: append-only double-entry ledger, Stripe webhook signature verification and `event.id` dedupe, idempotency keys on every Stripe write, explicit payment state machine.

### Product and compliance constraints
- Prohibited items: weapons, alcohol, tobacco/vapes, drugs and prescriptions, food, counterfeits, stolen goods.
- No university logos, mascots, or "official" wording. The footer states Tanu is independent and not affiliated with or endorsed by any university.
- Store datetimes in UTC; display in America/New_York (`TIME_ZONE`). Add a per-school time zone when a school outside Eastern time joins.
- V2 services: regulated categories (hair, nails, lashes, brows, esthetics) need a verified Maryland license before going live; no dorm-room service locations; tutoring may not include doing graded work.

## CI
- `.github/workflows/ci.yml`, path-filtered:
  - `backend/` or `contracts/` changes: ruff, migration check, contract check, pytest.
  - `web/` or `contracts/` changes: API-types check, lint, type check, build.
