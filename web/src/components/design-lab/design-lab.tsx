"use client";

import { useState, type ReactNode } from "react";

import { ListingCard } from "@/components/discovery/listing-card";
import { centsToDollars } from "@/lib/money";

import { StudentIdCard } from "@/components/profile/student-id-card";
import { schoolPalette } from "@/lib/school-colors";

import { HoldSlip, RequestRow } from "./deal-timers";
import { atSchool, LAB_LISTINGS } from "./lab-listings";
import { LAB_SCHOOLS, labSchool, type LabSchool } from "./lab-schools";
import { MeetupSchedulerMock } from "./meetup-scheduler";
import { TradePickerMock } from "./trade-picker";

const HOUR = 60 * 60 * 1000;
// Fixed so server and client render the same times. Thu Oct 8 2026, 6 PM Eastern.
const BASE = new Date("2026-10-08T22:00:00Z");

const STUDENTS: Record<string, { firstName: string; lastInitial: string; username: string; soldCount: number; dateJoined: string; bio: string }> = {
  umd: { firstName: "Maya", lastInitial: "R", username: "mayasells", soldCount: 14, dateJoined: "2026-08-20T16:00:00Z", bio: "Junior, cleaning out my closet before winter break. Meetups at Stamp or McKeldin." },
  towson: { firstName: "Devin", lastInitial: "K", username: "devink", soldCount: 3, dateJoined: "2026-09-03T16:00:00Z", bio: "Selling sneakers I don't wear anymore. Can meet near the Union." },
  umbc: { firstName: "Priya", lastInitial: "S", username: "priya.s", soldCount: 9, dateJoined: "2026-08-25T16:00:00Z", bio: "CS major. Calculators, textbooks, and the occasional jacket." },
  morgan: { firstName: "Jalen", lastInitial: "T", username: "jalent", soldCount: 21, dateJoined: "2026-07-14T16:00:00Z", bio: "Vintage and streetwear. Ask about bundles." },
};

function Section({ title, note, children }: { title: string; note: string; children: ReactNode }) {
  return (
    <section className="border-t border-line py-10">
      <h2 className="type-wide text-2xl font-black text-ink">{title}</h2>
      <p className="mt-2 max-w-2xl leading-6 text-muted">{note}</p>
      <div className="mt-6">{children}</div>
    </section>
  );
}

function SchoolChip({ school, selected, onSelect }: { school: LabSchool; selected: boolean; onSelect: () => void }) {
  const { lead, accent } = schoolPalette(school.colors);
  return (
    <button type="button" onClick={onSelect} aria-pressed={selected} className="chip">
      <span className="size-4 rounded-full" style={{ background: `linear-gradient(135deg, ${lead} 55%, ${accent} 55%)` }} aria-hidden="true" />
      {school.shortName}
    </button>
  );
}

export function DesignLab() {
  const [schoolSlug, setSchoolSlug] = useState("umd");
  const [hoursLater, setHoursLater] = useState(0);
  const [sellerConfirmed, setSellerConfirmed] = useState(true);
  const [buyerConfirmed, setBuyerConfirmed] = useState(false);
  const school = labSchool(schoolSlug);
  const now = new Date(BASE.getTime() + hoursLater * HOUR);

  const jacket = atSchool(LAB_LISTINGS.choreJacket, schoolSlug);
  const others = LAB_SCHOOLS.filter((option) => option.slug !== schoolSlug);
  const { hoodie, boots, bag, jeans, sneakers, leatherJacket, guitar, tee } = LAB_LISTINGS;
  const feed = [hoodie, boots, bag, jeans, sneakers, leatherJacket, guitar, tee].map((listing, index) => atSchool(listing, index < 3 ? schoolSlug : others[(index - 3) % others.length].slug));

  return (
    <div className="mx-auto max-w-6xl px-4 pt-8 pb-16 sm:px-6">
      <header className="flex flex-col gap-4 pb-8 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="type-wide text-4xl font-black text-ink">Design lab</h1>
          <p className="mt-2 max-w-xl leading-6 text-muted">Dev only. The real listing card and student ID with sample data, plus ideas not built yet. Pick a school to see its colors.</p>
        </div>
        <div className="flex flex-wrap gap-2" role="group" aria-label="School">
          {LAB_SCHOOLS.map((option) => <SchoolChip key={option.slug} school={option} selected={option.slug === schoolSlug} onSelect={() => setSchoolSlug(option.slug)} />)}
        </div>
      </header>

      <Section title="Listing card" note="The price hangs on the photo as a tag. Pending and Sold are stamps. A price drop (not built yet: needs price history) hangs a yellow tag over the crossed-out old one.">
        <div className="grid grid-cols-2 gap-x-4 gap-y-8 sm:grid-cols-4">
          <div><p className="mb-2 text-xs font-bold text-muted">Available</p><ListingCard listing={jacket} showSchool /></div>
          <div><p className="mb-2 text-xs font-bold text-muted">Price drop</p><ListingCard listing={jacket} showSchool previousPriceCents={4500} /></div>
          <div><p className="mb-2 text-xs font-bold text-muted">Pending</p><ListingCard listing={{ ...jacket, status: "pending" }} showSchool /></div>
          <div><p className="mb-2 text-xs font-bold text-muted">Sold</p><ListingCard listing={{ ...jacket, status: "sold" }} showSchool /></div>
        </div>
      </Section>

      <Section title="Mixed-school feed" note="The feed with All schools selected. The first three are from the selected school; the rest rotate through the others. Only the badge carries school color.">
        <div className="grid grid-cols-2 gap-x-4 gap-y-8 sm:grid-cols-3 lg:grid-cols-4">
          {feed.map((listing, index) => <ListingCard key={listing.id} listing={index === 3 ? { ...listing, status: "pending" } : listing} showSchool previousPriceCents={index === 5 ? listing.price_cents + 1000 : undefined} />)}
        </div>
      </Section>

      <Section title="Student ID profile" note="The profile header, shaped like a campus ID card. The stripe is the one place school colors fill space; everything else stays Tanu's.">
        <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,26rem)_1fr]">
          <StudentIdCard {...STUDENTS[schoolSlug]} schoolName={school.name} schoolColors={school.colors} nameAs="h3" />
          <div>
            <p className="max-w-prose leading-7 text-foreground/80">{STUDENTS[schoolSlug].bio}</p>
            <div className="mt-4 flex gap-2">
              <button type="button" className="btn btn-primary">Message</button>
              <button type="button" className="btn btn-secondary">Follow</button>
            </div>
          </div>
        </div>
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <p className="text-sm font-bold text-muted">Badges</p>
          {LAB_SCHOOLS.map((option) => {
            const palette = schoolPalette(option.colors);
            return <span key={option.slug} className="rounded-r px-2 py-1 text-xs font-extrabold" style={{ background: palette.lead, color: palette.text, boxShadow: `inset 3px 0 0 ${palette.accent}` }}>{option.shortName}</span>;
          })}
        </div>
      </Section>

      <Section title="Deal timers" note="Deadlines read as clock times in Eastern time. They turn red in the last 3 hours. Drag the slider to move time forward.">
        <label className="flex max-w-md flex-col gap-2 text-sm font-semibold text-ink">
          <span>{hoursLater === 0 ? "Now" : `${hoursLater} hours later`}</span>
          <input type="range" min={0} max={80} value={hoursLater} onChange={(event) => setHoursLater(Number(event.target.value))} className="accent-[var(--brand)]" />
        </label>
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-line p-4">
            <p className="text-sm font-bold text-muted">Seller&apos;s inbox: 24 hours to answer</p>
            <div className="divide-y divide-line">
              <RequestRow buyer="Jordan" action={`offered ${centsToDollars(3000)}`} image="/demo-listings/real/tan-washed-chore-jacket.jpg" receivedAt={new Date(BASE.getTime() - 5 * HOUR)} now={now} />
              <RequestRow buyer="Sam" action="wants to buy now" image="/demo-listings/real/timberland-wheat-boots.jpg" receivedAt={new Date(BASE.getTime() - 22 * HOUR)} now={now} />
            </div>
          </div>
          <div>
            <HoldSlip title="Tan chore jacket" price={centsToDollars(3600)} seller={STUDENTS[schoolSlug].firstName} buyer="Jordan" acceptedAt={new Date(BASE.getTime() - 26 * HOUR)} now={now} sellerConfirmed={sellerConfirmed} buyerConfirmed={buyerConfirmed} />
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="button" className="chip" aria-pressed={sellerConfirmed} onClick={() => setSellerConfirmed((value) => !value)}>Seller confirmed</button>
              <button type="button" className="chip" aria-pressed={buyerConfirmed} onClick={() => setBuyerConfirmed((value) => !value)}>Buyer confirmed</button>
            </div>
          </div>
        </div>
      </Section>

      <Section
        title="Guided meetup scheduling"
        note="A buyer chooses from the seller's preferred approved locations and automatically suggested times. The seller only has to confirm or suggest a change; chat stays available for exceptions."
      >
        <MeetupSchedulerMock />
      </Section>

      <Section
        title="Trade item selection"
        note="Three ways for the other party to choose exactly which available listings they want in exchange, with optional cash to balance the trade."
      >
        <TradePickerMock />
      </Section>
    </div>
  );
}
