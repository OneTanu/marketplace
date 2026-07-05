# Tanu

**A student-only marketplace for buying and selling on campus.**

Students list what they don't need anymore, like clothes, dorm furniture, textbooks, and electronics, and sell to other verified students at their school. Browse what was just listed, make an offer, message the seller, and meet up to hand it off.

> Tanu is an independent student project. It is not affiliated with or endorsed by any university.

## Features

- **Students only:** every account is verified with a school email address, and each school gets its own marketplace.
- **Listings and discovery:** photos, conditions, sizes, and filters, with a feed of what's new at your school.
- **Offers and messaging:** negotiate in the app, with clear Available, Pending, and Sold states.
- **Saved items and alerts:** bookmark listings, get price-drop alerts, and watch searches like "gray jeans under $30."
- **Trust built in:** reviews after every handoff, plus reporting and moderation.

*Coming next:* student services (tutoring, photography, and more) with in-app booking and payments, and a native mobile app.

## Tech stack

| Layer | Technology |
|---|---|
| Backend API | Python, Django, Django REST Framework |
| Database | PostgreSQL (full-text and trigram search) |
| Background jobs | Procrastinate (Postgres-backed queue) |
| Web app | Next.js, TypeScript, Tailwind CSS, installable as a PWA |
| Payments (planned) | Stripe Connect |
| Tooling | Docker, GitHub Actions, uv, OpenAPI-generated TypeScript types |

## Project structure

```
backend/     Django API: schools, accounts, listings, messaging, deals, reviews
web/         Next.js web app
contracts/   OpenAPI spec generated from the backend, shared with the web app
```

## Running locally

Requires Docker and Node.js.

```bash
docker compose up --build              # API at http://localhost:8000 (docs at /api/docs/)
cd web && npm install && npm run dev   # web app at http://localhost:3000
```

## Status

Early development, starting at the University of Maryland.
