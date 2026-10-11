import card from "@/components/discovery/listing-card.module.css";

import styles from "./design-lab.module.css";

const HOUR = 60 * 60 * 1000;
const ZONE = "America/New_York";
const URGENT_HOURS = 3;

const dayKey = (date: Date) => date.toLocaleDateString("en-CA", { timeZone: ZONE });
const clock = (date: Date) => date.toLocaleTimeString("en-US", { timeZone: ZONE, hour: "numeric", minute: "2-digit" }).replace(":00", "");
const weekday = (date: Date) => date.toLocaleDateString("en-US", { timeZone: ZONE, weekday: "short" });

// "4:15 PM today", "6 PM tomorrow", "6 PM Sat": students plan around clock times.
export function formatDeadline(deadline: Date, now: Date) {
  // Step the calendar date, not 24 hours, so DST days (23 or 25 hours) still say "tomorrow".
  const tomorrow = new Date(`${dayKey(now)}T00:00:00Z`);
  tomorrow.setUTCDate(tomorrow.getUTCDate() + 1);
  const day = dayKey(deadline) === dayKey(now) ? "today" : dayKey(deadline) === tomorrow.toISOString().slice(0, 10) ? "tomorrow" : weekday(deadline);
  return `${clock(deadline)} ${day}`;
}

function timeLeft(ms: number) {
  const hours = Math.floor(ms / HOUR);
  if (hours >= 1) return `${hours} ${hours === 1 ? "hour" : "hours"} left`;
  return `${Math.max(1, Math.round(ms / 60000))} min left`;
}

export function RequestRow({ buyer, action, image, receivedAt, now }: {
  buyer: string;
  action: string;
  image: string;
  receivedAt: Date;
  now: Date;
}) {
  const deadline = new Date(receivedAt.getTime() + 24 * HOUR);
  const remaining = deadline.getTime() - now.getTime();
  const expired = remaining <= 0;
  const urgent = !expired && remaining < URGENT_HOURS * HOUR;
  const used = Math.min(100, ((now.getTime() - receivedAt.getTime()) / (24 * HOUR)) * 100);

  return (
    <div className="flex items-center gap-3 py-3">
      <div className="h-14 w-11 shrink-0 rounded-md bg-surface bg-cover bg-center" style={{ backgroundImage: `url(${image})` }} />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-bold text-ink">{buyer} {action}</p>
        <p className={`mt-0.5 text-[13px] ${urgent ? "font-bold text-[var(--danger)]" : "text-muted"}`}>
          {expired ? "Expired. The buyer was told to look at other listings." : `Answer by ${formatDeadline(deadline, now)}, ${timeLeft(remaining)}`}
        </p>
        <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-surface"><div className={`h-full ${urgent || expired ? "bg-[var(--danger)]" : "bg-ink"}`} style={{ width: `${used}%` }} /></div>
      </div>
      <button type="button" disabled={expired} className="btn btn-secondary btn-sm">Reply</button>
    </div>
  );
}

export function HoldSlip({ title, price, seller, buyer, acceptedAt, now, sellerConfirmed, buyerConfirmed }: {
  title: string;
  price: string;
  seller: string;
  buyer: string;
  acceptedAt: Date;
  now: Date;
  sellerConfirmed: boolean;
  buyerConfirmed: boolean;
}) {
  const deadline = new Date(acceptedAt.getTime() + 72 * HOUR);
  const remaining = deadline.getTime() - now.getTime();
  const sold = sellerConfirmed && buyerConfirmed;
  const released = !sold && remaining <= 0;
  const urgent = !sold && !released && remaining < URGENT_HOURS * HOUR;
  const elapsedDays = (now.getTime() - acceptedAt.getTime()) / (24 * HOUR);

  const heading = sold ? "Sold" : released ? "Back on the rack" : `On hold until ${formatDeadline(deadline, now)}`;
  const footnote = sold
    ? `${seller} and ${buyer} both confirmed the handoff.`
    : released
      ? "Nobody confirmed the handoff in 72 hours, so it's Available again."
      : `When both boxes are checked it's sold. If not, it goes back to Available at ${formatDeadline(deadline, now)}.`;

  return (
    <div className="overflow-hidden rounded-lg border-[1.5px] border-ink bg-background">
      <div className="flex items-start justify-between gap-3 p-4">
        <div>
          <p className={`type-wide text-xl font-black leading-tight ${urgent ? "text-[var(--danger)]" : "text-ink"}`}>{heading}</p>
          <p className="mt-1 text-[13px] text-muted">{title}, {price}, for {buyer}</p>
        </div>
        {!released && <span className={`${card.stamp} shrink-0 ${sold ? "text-[#d42b33]" : "text-brand"}`}>{sold ? "SOLD" : "PENDING"}</span>}
      </div>
      <div className={`grid grid-cols-3 ${styles.perforated}`}>
        {[0, 1, 2].map((day) => {
          const fill = Math.min(1, Math.max(0, elapsedDays - day));
          const ends = new Date(acceptedAt.getTime() + (day + 1) * 24 * HOUR);
          return <div key={day} className="relative px-3 py-2 text-xs font-bold text-ink">
            <div className="absolute inset-y-0 left-0 bg-ink/15" style={{ width: `${fill * 100}%` }} aria-hidden="true" />
            <span className="relative">Day {day + 1}<span className="block font-medium text-muted">Ends {weekday(ends)}</span></span>
          </div>;
        })}
      </div>
      <ul className="grid gap-1.5 border-t-[1.5px] border-ink px-4 py-3 text-[13px] text-ink">
        {[[seller, "handed it off", sellerConfirmed], [buyer, "got it", buyerConfirmed]].map(([name, verb, done]) => <li key={String(verb)} className="flex items-center gap-2">
          <span className={`grid size-4 place-items-center rounded border-[1.5px] border-ink text-[10px] font-black ${done ? "bg-ink text-white" : ""}`} aria-hidden="true">{done ? "✓" : ""}</span>
          <span>{name} {verb}{done ? "" : <span className="sr-only"> (not yet)</span>}</span>
        </li>)}
      </ul>
      <p className="px-4 pb-4 text-xs leading-5 text-muted">{footnote}</p>
    </div>
  );
}
