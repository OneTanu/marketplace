# Product

<!-- impeccable:product-schema 1 -->
<!-- Written Nov 13, 2026 from AGENTS.md and the redesign spec, for design tools (Impeccable) and new contributors. AGENTS.md is the source of truth if they ever disagree. -->

## Platform

web

## Users

Verified college students buying and selling used items on their own campus, starting at the University of Maryland. Mostly on a phone, often one-handed between classes. A buyer browses their school's feed, saves or asks for an item, then meets the seller on campus. A seller posts from their phone in a couple of minutes and answers requests from the Deals page.

## Product Purpose

A student-only marketplace: every account is tied to a verified school email, and each user and listing belongs to one school. Success is an item changing hands safely between two students, with the handoff confirmed by both.

## Positioning

Everyone on it is a verified student at your school, and the item is a walk away. A general marketplace can't say either.

## Operating Context

- Payment happens off-platform (cash, Venmo, Zelle). Buy now and offers are requests, never a commitment to pay.
- Item status: Available → Pending (seller accepted a buyer) → Sold (both confirmed the handoff).
- Timers: 24h to answer a request or offer; 72h for a Pending deal to be confirmed.
- Meetups are on campus, at public spots.
- Installable as a PWA. Phone layout first, widened for desktop (the layout switches at 1024px).

## Capabilities and Constraints

- V1 is items only. Services, bookings and on-platform payment are V2.
- Prohibited: weapons, alcohol, tobacco and vapes, drugs and prescriptions, food, counterfeits, stolen goods.
- Feeds and searches show the viewer's school unless they widen the scope.
- Money is integer cents with a currency. Times display in America/New_York.
- Dark mode is out of scope for the current redesign.

## Brand Commitments

- Name: Tanu, written lowercase as the wordmark "tanu".
- Visual direction "Hang tag" (approved Nov 11, 2026): ink, kraft and stretched Archivo. Kraft is for the price tag only. Signal pink is for "needs you" and unread counts only. DESIGN.md has the full system.
- No university logos, mascots or "official" wording. The footer says Tanu is independent and not affiliated with or endorsed by any university. School colors appear only on the profile card stripe and the school badge.

## Evidence on Hand

- Development and audit listings use real item photos: the ones committed in `web/public/demo-listings/real/`, plus public-domain (CC0) stock photos kept locally with their sources. No production photography yet.
- No testimonials, press or usage numbers. Don't invent any.

## Product Principles

1. One next step: at most one filled button per screen and per card.
2. One place per job: each task has one home; other entry points link to it.
3. Phone first, decided by width. Touch targets are at least 44px; text you read is 16px; nothing under 13px.
4. Ask late, default well: pre-fill what the app can decide.
5. Every action has an after: say what happened and what comes next.
6. Say it once: one status line per item, one safety note per flow.

## Accessibility & Inclusion

Visible keyboard focus, 44px touch targets and 16px form fields are already enforced. No formal WCAG level has been set.
