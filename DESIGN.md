---
name: Tanu
description: A student-only campus marketplace that looks like a thrift-store hang tag.
colors:
  ink: "#17162b"
  ink-strong: "#34324f"
  ink-soft: "#efeef5"
  kraft: "#d7b98e"
  kraft-soft: "#f3e9d7"
  signal: "#dc2463"
  signal-soft: "#fde8ef"
  signal-ink: "#a3103f"
  paper: "#ffffff"
  surface: "#f3f2f7"
  line: "#e4e3eb"
  muted: "#6b6a7b"
  danger: "#c0262d"
  danger-soft: "#fdf0f0"
  success: "#15803d"
  success-soft: "#edf8f1"
  warning: "#b45309"
  warning-soft: "#fdf5e6"
typography:
  display:
    fontFamily: "Archivo, Arial, Helvetica, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 800
    lineHeight: "2rem"
    letterSpacing: "-0.02em"
    fontVariation: "'wdth' 125"
  title:
    fontFamily: "Archivo, Arial, Helvetica, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 800
    lineHeight: "1.5rem"
    letterSpacing: "-0.02em"
    fontVariation: "'wdth' 125"
  body:
    fontFamily: "Archivo, Arial, Helvetica, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: "1.5rem"
  label:
    fontFamily: "Archivo, Arial, Helvetica, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: "1.25rem"
  fine:
    fontFamily: "Archivo, Arial, Helvetica, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: "1.125rem"
rounded:
  lg: "8px"
  xl: "12px"
  full: "9999px"
spacing:
  step: "4px"
  gutter-phone: "16px"
  gutter-tablet: "24px"
  gutter-desktop: "32px"
  grid-gap-x: "12px"
  grid-gap-y: "24px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.lg}"
    padding: "0 20px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.ink-strong}"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "0 20px"
    height: "44px"
  button-secondary-hover:
    backgroundColor: "{colors.surface}"
  button-danger:
    backgroundColor: "{colors.danger-soft}"
    textColor: "{colors.danger}"
    rounded: "{rounded.lg}"
    height: "44px"
  chip:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.full}"
    padding: "0 14px"
    height: "44px"
  chip-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  field:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "0 16px"
    height: "48px"
  price-tag:
    backgroundColor: "{colors.kraft}"
    textColor: "{colors.ink}"
    typography: "{typography.title}"
  count-badge:
    backgroundColor: "{colors.signal}"
    textColor: "{colors.paper}"
    rounded: "{rounded.full}"
    height: "20px"
---

# Design System: Tanu

The tokens live in `web/src/app/globals.css`, the shared parts in `web/src/components/ui/`, and `/dev/styleguide` shows all of them (development only). The lint rule `web/eslint-rules/design-tokens.mjs` rejects sizes, weights, corners, shadows, colours (including Tailwind's palette and `dark:` classes) and icons that aren't defined here. It checks class strings in `.ts`/`.tsx`, not CSS modules; layout one-offs like `aspect-[4/5]` or `max-w-[26rem]` are allowed. Decisions and mockups: `docs/design-audit/spec.md`, "Slice 1c decisions" (local only).

## Overview

**Creative North Star: "The Hang Tag"**

Tanu looks like the tag on a thrift-store find: near-black ink on white paper, one kraft-brown tag carrying the price, and a wide, heavy grotesque for the few words that matter. The photos carry the colour; everything around them stays quiet. Students use it on a phone between classes, so the brand shows up in a few precise details (the wordmark, the hanging price tag, the rubber stamps for Pending and Sold, the ID-shaped profile card) and the rest is plain, consistent and fast.

**Key Characteristics:**
- Ink does the work: text, the filled button, focus rings and selected states are one near-black.
- One accent per job: kraft is the price tag; signal pink means something is waiting on you.
- Five type roles and three weights. Stretched Archivo for titles and prices only.
- Flat white pages wherever there are photos; a grey page with white cards on account and settings pages.
- One icon family (Lucide), 2px lines. Small, quick motion that confirms a touch.

## Colors

A two-ink palette on white: a blue-black ink and a kraft brown, with one hot pink reserved for attention.

### Primary
- **Ink** (`ink`): body text, headings, the filled button, selected chips, the focus ring, the current tab.
- **Ink, pressed** (`ink-strong`): hover on the filled button.

### Secondary
- **Kraft** (`kraft`): the price tag. Too pale for text on white, and used nowhere else.
- **Kraft wash** (`kraft-soft`): text selection.

### Tertiary
- **Signal pink** (`signal`): unread counts and the dot on the "needs you" strip and badge. 4.7:1 under white 13px text. The "Needs you" badge is `signal-ink` text on `signal-soft` (6.6:1).

### Neutral
- **Paper** (`paper`): page and card background.
- **Surface** (`surface`): the search field, skeletons, quiet panels, and the page itself on account pages.
- **Line** (`line`): hairlines, row dividers, the secondary button's border.
- **Muted** (`muted`): secondary text, 5.3:1 on paper.
- **Danger, success, warning**, each with a soft tint: status text, badges, notices. Danger is also the saved heart and the Sold stamp.

### Avatar tints
Five pairs (`tint-1` to `tint-5`, each with an `-ink` text colour): soft blue, green, rose, violet and sand. A person's tint comes from their username, so they look the same everywhere.

### Named Rules
**The One Tag Rule.** Kraft appears on the price tag. Kraft on a button, a link, a badge or a background is wrong; the lint rule rejects `*-kraft` classes.
**The Needs-You Rule.** Signal pink marks something waiting on the viewer. It is never decoration.

## Typography

**Display and Title:** Archivo at width 125 (`type-wide`), weight 800.
**Body, Label, Fine:** Archivo at normal width.

**Character:** one family doing two jobs. Stretched and heavy it reads like a garment label; at normal width it's a plain, legible grotesque.

### Hierarchy
- **Display** (800, 28/32, stretched): page titles, the price on a listing page.
- **Title** (800, 18/24, stretched): section titles, names, sheet titles. The price tag is the same weight at 16px.
- **Body** (400, 16/24): text people read, every form field (16px stops iPhones zooming), list rows (600).
- **Label** (600, 14/20): buttons, card titles, nav links; 400 for small helper text.
- **Fine** (400, 13/18): details under a card, chips (600), badges (600), bottom-bar labels. Nothing is smaller.

Classes: `text-display`, `text-title`, `text-body`, `text-label`, `text-fine`; weights `font-normal`, `font-semibold`, `font-extrabold`. Tailwind's own sizes and weights are switched off.

### Named Rules
**The Label Rule.** Width 125 is for Display, Title, prices and the wordmark. Body copy, buttons and list rows are never stretched.
**The Two Exceptions.** The "tanu" wordmark (`wordmark`, 22px, 26px on desktop) is a logo, not text. The guest Home headline (`text-hero`) keeps its marketing size until slice 6 redesigns that page. Nothing else may use either.

## Layout

Phone first, switched by width. Under 1024px: a sticky 64px header (wordmark, search, bell) and a fixed, opaque five-item bottom bar. From 1024px the bottom bar goes and the header carries Deals, Inbox, the bell, Sell and the account menu. Content sits in a 1152px container with a 16px gutter on phones, 24px from 640px. Listing grids are 2 columns on phones, 3 from 640px and 4 from 1024px, with 12 to 16px between columns and 24 to 32px between rows. Single-task pages (the account hub, forms) use one 448px column. Spacing steps by 4px; use 4, 8, 12, 16, 24, 32 and 48 (8 inside a group, 16 between groups, 32 between sections). Every control is at least 44px tall; fields are 48px.

## Elevation & Depth

Flat by default. Pages with listing photos are white, and things separate with a 1px line or the surface tint. Account and settings pages (the hub today; the rest as their slices land) sit on the grey `surface` page, opted in with `data-page-tint`, and their content is white cards that lift slightly off it.

### Shadow Vocabulary
- **Float** (`shadow-float`, `0 1px 2px rgb(23 22 43 / .12)`): things that sit on a photo, like the heart button.
- **Card** (`shadow-card`, `0 1px 2px rgb(23 22 43 / .06), 0 8px 24px -12px rgb(23 22 43 / .18)`): white cards on the grey account page, and the ID card.
- **Overlay** (`shadow-overlay`, `0 16px 40px -12px rgb(23 22 43 / .22)`): menus (which add a 1px line border), sheets, dialogs.

### Named Rules
**The Photos-Stay-White Rule.** The grey page appears only where there are no listing photos. Listings never sit in boxed cards.

## Shapes

Three corners: `rounded-lg` (8px) for buttons, fields and small controls (the one exception: a hand-drawn checkbox keeps a 4px corner, `.checkbox`, so it doesn't read as a radio button); `rounded-xl` (12px) for photos, cards, sheets, dialogs and menus; `rounded-full` for chips, avatars, badges and round icon buttons. The signature shapes are cut, not rounded: the price tag is a clipped pentagon with a punched hole, tilted -3°; Pending and Sold are tilted rubber stamps with a 3px border. The profile card keeps a real campus ID's proportions (85.6 × 54).

## Components

### Buttons (`.btn` classes)
- **Shape:** 8px corners, 44px tall (48px with `btn-lg` for the main action in a sheet), Label type.
- **Primary** (`btn-primary`): ink fill, white text. One per screen.
- **Secondary** (`btn-secondary`): white with a 1px line border; hover fills surface.
- **Quiet** (`btn-quiet`): text only. **Danger** (`btn-danger`): red text on the soft red.
- **States:** pressed scales to 0.97 in 120ms; disabled is 50% opacity; hover only on devices with a mouse.

### Chips (`.chip`)
- 44px pill, 1px line border, Fine type at 600. Selected (`aria-pressed`, `aria-current`, `aria-expanded`) is ink with white text.

### Fields (`.field`)
- 48px, 1px line border, 8px corners, 16px text. Focus turns the border ink with a soft 3px ink ring.

### List rows (`ListRow`, `ListButton`, `ListGroup`)
- 56px rows, Body type at 600, an optional 22px icon, an optional muted value, a chevron. Grouped in a white card with hairlines; Log out sits in its own group, muted.

### Cards and skeletons (`Card`, `Skeleton`)
- `Card` is white with 12px corners: `lifted` (shadow-card) on grey pages, `line` (hairline) on white ones. `Skeleton` is a surface box with a soft shimmer that stops under reduced motion.

### Badges (`Badge`, `CountBadge`)
- 24px pills in Fine type at 600: needs (pink tint with a dot), pending, ok, sold (ink), neutral, danger. `CountBadge` is the pink unread count, capped at 99+.

### Avatar (`Avatar`)
- Round, the first initial in stretched type on the person's tint. 36px (`sm`), 44px (`md`), 76px on phones and 88px on desktop (`lg`, the ID card).

### Price tag (`PriceTag`)
- The signature. Kraft pentagon with a punched hole, 16px stretched price at 800, tilted -3°, a thin drop shadow so it holds on tan photos. On a listing card it hangs off the photo's bottom edge, half on and half off, so it never covers the item. A price drop puts the old price, struck through, beside a yellow tag.

### Profile card (`StudentIdCard`)
- A campus ID at 85.6 × 54: the school's stripe across the top (the only place school colours fill space), the round avatar, the name once, @username, school, sold and followers, the join date. No logos, seals, numbers or barcodes.

### Sheet (`Sheet`)
- Built on `<dialog>`. A bottom sheet on phones (12px top corners, a grab bar) and a 448px centred dialog on desktop. In 280ms on the sheet curve, out 200ms; with reduced motion it only fades. The dimmed area and Escape close it.

### Navigation
- Header links are Label type, muted, ink with a 2px underline when current. The bottom bar is five equal columns: a 24px Lucide icon over a Fine label; the current tab is ink with a 2.4px line (Lucide has no filled icons); Sell is a filled ink circle.

### Icons
- Lucide only, through `web/src/components/ui/icons.tsx` (the lint rule blocks inline `<svg>` and direct `lucide-react` imports). 2px lines on a 24px grid; a saved heart is the outline filled in. Two drawings live in the same file because Lucide lacks them: the Instagram glyph and the 404 page's blank tag.

### Motion
- Press 120ms (scale 0.97), colour and state 160ms, sheet or dialog in 280ms and out 200ms, photo hover zoom 300ms. Ease-out `cubic-bezier(0.23, 1, 0.32, 1)`; sheets `cubic-bezier(0.32, 0.72, 0, 1)`. Hover effects only under `(hover: hover)`. Reduced motion drops movement and keeps fades. No animation on things used hundreds of times a day beyond the press.

## Do's and Don'ts

### Do:
- **Do** use ink for anything a student can press, and for the focus ring.
- **Do** keep form fields at 16px and controls at 44px or taller.
- **Do** let photos carry the colour; chrome stays white, grey and ink.
- **Do** show each fact once per screen: one status line, one username.
- **Do** take icons from `ui/icons.tsx` and parts from `components/ui/` before writing new ones.

### Don't:
- **Don't** use kraft anywhere but the price tag, or signal pink for anything but "needs you" and counts.
- **Don't** stretch body copy, buttons or list rows, or set text under 13px.
- **Don't** add a second filled button to a screen or a card.
- **Don't** put listings in boxed cards or on the grey page.
- **Don't** use university logos, mascots or "official" wording. School colours appear only on the ID card stripe and the school badge.
