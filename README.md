# Tanu

**A marketplace for UMD students to offer and book services from each other.**

Students list what they're good at, like tutoring, photography, design, or hair and beauty. Other students find them, book a time, and pay securely in the app. Providers get paid once the job is done.

> Tanu is an independent student project. It is not affiliated with or endorsed by the University of Maryland.

## Features

- **UMD-only community:** every account is verified with a university email address.
- **Service listings and booking:** browse providers, see availability, book an appointment.
- **Secure payments:** customers pay at booking and providers are paid after completion, via Stripe Connect.
- **Trust built in:** reviews, reporting, and license checks for regulated services like hair and nails.

*Coming next:* a buy-and-sell marketplace for items, messaging, and a mobile app.

## Tech stack

| Layer | Technology |
|---|---|
| Backend API | Python, Django, Django REST Framework |
| Database | PostgreSQL |
| Background jobs | Procrastinate (Postgres-backed queue) |
| Payments | Stripe Connect |
| Web app | Next.js, TypeScript, Tailwind CSS |
| Mobile app | React Native (Expo), planned |
| Tooling | Docker, GitHub Actions, uv |

## Project structure

```
backend/     Django API: accounts, listings, bookings, payments, reviews
web/         Next.js web app
contracts/   OpenAPI spec generated from the backend, shared by web and mobile
```

## Running locally

Requires Docker and Node.js.

```bash
docker compose up --build        # API at http://localhost:8000 (docs at /api/docs/)
cd web && npm install && npm run dev   # web app at http://localhost:3000
```

## Status

Early development. The core booking and payments system is being built first.
