"use client";

import { useState, type ReactNode } from "react";

import { LAB_LISTINGS } from "@/components/design-lab/lab-listings";
import { ListingCard } from "@/components/discovery/listing-card";
import { StudentIdCard } from "@/components/profile/student-id-card";
import { Avatar } from "@/components/ui/avatar";
import { Badge, CountBadge } from "@/components/ui/badge";
import { Card, Skeleton } from "@/components/ui/card";
import {
  BellIcon, BookmarkIcon, CheckIcon, ChevronDownIcon, ChevronLeftIcon, ChevronRightIcon, CloseIcon, DealsIcon, FiltersIcon, HeartIcon, HomeIcon,
  InboxIcon, LogOutIcon, MapPinIcon, ModerationIcon, PlusIcon, ProfileIcon, SearchIcon, SendIcon, ShareIcon, ShieldCheckIcon, SortIcon, StoreIcon,
} from "@/components/ui/icons";
import { ListButton, ListGroup, ListRow } from "@/components/ui/list-row";
import { PriceTag } from "@/components/ui/price-tag";
import { Sheet } from "@/components/ui/sheet";

const COLOURS: [string, string][] = [
  ["ink", "Text, filled buttons, focus, selected"],
  ["muted", "Secondary text"],
  ["line", "Hairlines and secondary button borders"],
  ["surface", "Search field, skeletons, the grey account page"],
  ["background", "Page and cards"],
  ["kraft", "The price tag, nothing else"],
  ["signal", "Needs you and unread counts only"],
  ["danger", "Errors and destructive actions"],
  ["success", "Done and available"],
  ["warning", "Pending and deadlines"],
];
const ROLES: [string, string, string][] = [
  ["Display", "type-wide text-display font-extrabold", "28/32 · 800 · stretched · page titles"],
  ["Title", "type-wide text-title font-extrabold", "18/24 · 800 · stretched · sections, names, the tag"],
  ["Body", "text-body", "16/24 · 400 · text you read, fields, rows"],
  ["Label", "text-label font-semibold", "14/20 · 600 · buttons, card titles, nav"],
  ["Fine", "text-fine text-muted", "13/18 · 400 · details, chips, bar labels"],
];
const ICONS = { HomeIcon, DealsIcon, PlusIcon, InboxIcon, ProfileIcon, HeartIcon, BellIcon, SearchIcon, FiltersIcon, SortIcon, StoreIcon, MapPinIcon, ShieldCheckIcon, ModerationIcon, LogOutIcon, BookmarkIcon, ShareIcon, SendIcon, CheckIcon, CloseIcon, ChevronLeftIcon, ChevronRightIcon, ChevronDownIcon };

function Section({ title, note, children }: { title: string; note?: string; children: ReactNode }) {
  return (
    <section className="border-t border-line py-8 first:border-t-0">
      <h2 className="type-wide text-title font-extrabold">{title}</h2>
      {note && <p className="mt-1 max-w-2xl text-label text-muted">{note}</p>}
      <div className="mt-5">{children}</div>
    </section>
  );
}

export function Styleguide() {
  const [sheet, setSheet] = useState(false);
  const [chip, setChip] = useState("All");

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <h1 className="type-wide text-display font-extrabold">Styleguide</h1>
      <p className="mt-2 max-w-2xl text-body text-muted">Every token and shared part, as the app uses them. DESIGN.md explains the rules; the design-tokens lint rule enforces them.</p>

      <Section title="Colour">
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {COLOURS.map(([name, use]) => <li key={name}><div className="h-14 rounded-xl border border-line" style={{ background: `var(--${name})` }} /><p className="mt-2 text-label font-semibold">{name}</p><p className="text-fine text-muted">{use}</p></li>)}
        </ul>
      </Section>

      <Section title="Type roles" note="Five roles and three weights (400, 600, 800). Nothing under 13px; text people read is 16.">
        <ul className="divide-y divide-line">
          {ROLES.map(([name, cls, spec]) => <li key={name} className="flex flex-wrap items-baseline gap-x-6 gap-y-1 py-3"><span className="w-20 text-fine text-muted">{name}</span><span className={`w-full min-w-0 [overflow-wrap:anywhere] sm:w-auto sm:flex-1 ${cls}`}>New at UMD: Squier Stratocaster</span><span className="text-fine text-muted">{spec}</span></li>)}
        </ul>
      </Section>

      <Section title="Corners, depth, spacing" note="8 for controls, 12 for photos, cards and sheets, full for chips and avatars. Pages are flat; cards lift only on the grey account pages. Gaps step by 4: 4, 8, 12, 16, 24, 32, 48.">
        <div className="flex flex-wrap gap-6">
          <div className="grid size-24 place-items-center rounded-lg border border-line text-fine">rounded-lg</div>
          <div className="grid size-24 place-items-center rounded-xl border border-line text-fine">rounded-xl</div>
          <div className="grid size-24 place-items-center rounded-full border border-line text-fine">full</div>
          <div className="grid h-24 w-36 place-items-center rounded-xl bg-background text-fine shadow-float">shadow-float</div>
          <div className="grid h-24 w-36 place-items-center rounded-xl bg-background text-fine shadow-card">shadow-card</div>
          <div className="grid h-24 w-36 place-items-center rounded-xl bg-background text-fine shadow-overlay">shadow-overlay</div>
        </div>
      </Section>

      <Section title="Icons" note="Lucide, 2px lines on a 24px grid, imported from components/ui/icons.tsx. No filled icons: a current tab is ink at 2.4px, a saved heart is the outline filled in.">
        <ul className="grid grid-cols-4 gap-4 sm:grid-cols-8">
          {Object.entries(ICONS).map(([name, Icon]) => <li key={name} className="flex flex-col items-center gap-2 text-center"><Icon className="size-6" aria-hidden="true" /><span className="text-fine text-muted">{name.replace("Icon", "")}</span></li>)}
          <li className="flex flex-col items-center gap-2 text-center"><HeartIcon className="size-6 text-danger" fill="currentColor" aria-hidden="true" /><span className="text-fine text-muted">Saved</span></li>
        </ul>
      </Section>

      <Section title="Buttons" note="One filled button per screen. Secondary is white with a hairline. Pressed buttons shrink 3% (120ms).">
        <div className="flex flex-wrap items-center gap-3">
          <button type="button" className="btn btn-primary">Buy now</button>
          <button type="button" className="btn btn-secondary">Make offer</button>
          <button type="button" className="btn btn-quiet">Cancel</button>
          <button type="button" className="btn btn-danger">Decline</button>
          <button type="button" className="btn btn-primary" disabled>Sending…</button>
          <button type="button" className="btn btn-secondary btn-sm">Small</button>
          <button type="button" className="btn btn-primary btn-lg">Send request</button>
        </div>
      </Section>

      <Section title="Chips, badges, fields">
        <div className="flex flex-wrap gap-2">
          {["All", "Under $25", "Size M"].map((label) => <button key={label} type="button" aria-pressed={chip === label} onClick={() => setChip(label)} className="chip">{label}</button>)}
        </div>
        <div className="mt-5 flex flex-wrap items-center gap-2">
          <Badge tone="needs">Needs you</Badge><Badge tone="pending">Pending</Badge><Badge tone="ok">Available</Badge><Badge tone="sold">Sold</Badge><Badge tone="danger">Canceled</Badge><Badge>Indoors</Badge><CountBadge count={3} /><CountBadge count={120} />
        </div>
        <div className="mt-5 grid max-w-md gap-3">
          <label className="grid gap-1.5 text-label font-semibold">Your offer<input className="field font-normal" placeholder="$30" inputMode="decimal" /></label>
        </div>
      </Section>

      <Section title="Avatars" note="Round, with one of five tints picked from the username.">
        <div className="flex flex-wrap items-center gap-3">
          {["josh", "maya_t", "andre.k", "kayla_r", "sam"].map((username) => <Avatar key={username} user={{ username }} />)}
          <Avatar user={{ first_name: "Josh", username: "josh" }} size="sm" />
          <Avatar user={{ first_name: "Josh", username: "josh" }} size="lg" />
        </div>
      </Section>

      <Section title="List rows and cards" note="On the grey account pages rows sit in white cards; Log out stands apart.">
        <div className="grid gap-6 rounded-xl bg-surface p-4 sm:grid-cols-2 sm:p-6">
          <div>
            <StudentIdCard firstName="Josh" lastInitial="B" username="audit_seller" schoolName="University of Maryland" schoolColors={["#e21833", "#ffd200", "#000000"]} dateJoined="2026-11-01T12:00:00Z" soldCount={12} followerCount={48} nameAs="h3" />
            <ListGroup className="mt-4">
              <ListRow href="/listings/mine" icon={StoreIcon} value="4">My listings</ListRow>
              <ListRow href="/profile/saved" icon={HeartIcon}>Saved</ListRow>
              <ListRow href="/profile/standing" icon={ShieldCheckIcon} value="Good">Account status</ListRow>
            </ListGroup>
            <ListGroup className="mt-4"><ListButton onClick={() => {}} icon={LogOutIcon} tone="muted">Log out</ListButton></ListGroup>
          </div>
          <div className="grid content-start gap-4">
            <Card className="p-4"><p className="type-wide text-title font-extrabold">Nothing saved yet</p><p className="mt-1 text-label text-muted">Tap the heart on a listing to keep it here.</p><button type="button" className="btn btn-primary mt-4">Browse listings</button></Card>
            <Card tone="line" className="p-4"><p className="text-label font-semibold">A hairline card</p><p className="mt-1 text-fine text-muted">For panels on the white pages.</p></Card>
            <Card className="grid grid-cols-2 gap-3 p-4"><div><Skeleton className="aspect-[4/5]" /><Skeleton className="mt-2.5 h-3 w-4/5 rounded-full" /></div><div><Skeleton className="aspect-[4/5]" /><Skeleton className="mt-2.5 h-3 w-3/5 rounded-full" /></div></Card>
          </div>
        </div>
      </Section>

      <Section title="Listing card and price tag" note="The tag hangs off the photo's bottom edge, so it never covers the item. A price drop shows the old price struck through.">
        <ul className="grid grid-cols-2 gap-x-3 gap-y-6 sm:grid-cols-4 sm:gap-x-4 sm:gap-y-8">
          <li><ListingCard listing={LAB_LISTINGS.boots} showBookmark /></li>
          <li><ListingCard listing={LAB_LISTINGS.choreJacket} previousPriceCents={4800} showBookmark /></li>
          <li><ListingCard listing={{ ...LAB_LISTINGS.bag, status: "pending" }} showBookmark /></li>
          <li><ListingCard listing={{ ...LAB_LISTINGS.guitar, status: "sold" }} /></li>
        </ul>
        <div className="mt-6 flex flex-wrap items-center gap-4"><PriceTag label="$36" hanging={false} /><PriceTag label="Free" hanging={false} /><PriceTag label="$1,250" hanging={false} /></div>
      </Section>

      <Section title="Sheet" note="A bottom sheet on phones and a centred dialog on desktop: in 280ms, out 200ms.">
        <button type="button" className="btn btn-primary" onClick={() => setSheet(true)}>Open the sheet</button>
        <Sheet open={sheet} onClose={() => setSheet(false)} title="Buy now">
          <div className="flex items-center gap-3 rounded-xl bg-surface p-3">
            <span className="min-w-0 flex-1"><span className="block text-label font-semibold">Stamp Student Union</span><span className="text-fine text-muted">Thu 8:00 AM</span></span>
            <button type="button" className="btn btn-quiet btn-sm">Change</button>
          </div>
          <button type="button" className="btn btn-primary btn-lg mt-4 w-full" onClick={() => setSheet(false)}>Send request</button>
        </Sheet>
      </Section>
    </div>
  );
}
