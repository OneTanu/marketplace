"use client";

import { useMemo, useState } from "react";

type Spot = {
  id: string;
  name: string;
  detail: string;
  note: string;
  indoor: boolean;
};

type Day = {
  id: string;
  label: string;
  date: string;
  times: string[];
};

const SPOTS: Spot[] = [
  {
    id: "mckeldin",
    name: "McKeldin Library",
    detail: "Main entrance · by the security desk",
    note: "Indoors, staffed, and usually busy",
    indoor: true,
  },
  {
    id: "stamp",
    name: "Stamp Student Union",
    detail: "Ground floor · information desk",
    note: "Indoors, staffed, and well lit",
    indoor: true,
  },
  {
    id: "south-campus",
    name: "South Campus Dining Hall",
    detail: "Outside the main entrance",
    note: "High foot traffic during dining hours",
    indoor: false,
  },
];

const DAYS: Day[] = [
  { id: "today", label: "Today", date: "Oct 12", times: ["5:30 PM", "6:00 PM", "6:30 PM"] },
  { id: "tomorrow", label: "Tomorrow", date: "Oct 13", times: ["4:30 PM", "5:00 PM", "6:00 PM"] },
  { id: "wednesday", label: "Wednesday", date: "Oct 14", times: ["4:00 PM", "5:30 PM", "6:30 PM"] },
];

function SellerPreferencesMock() {
  const windows = [
    { day: "Monday", value: "4:00 PM–7:00 PM", enabled: true },
    { day: "Tuesday", value: "Unavailable", enabled: false },
    { day: "Wednesday", value: "5:00 PM–8:00 PM", enabled: true },
    { day: "Thursday", value: "4:00 PM–6:30 PM", enabled: true },
    { day: "Friday", value: "Unavailable", enabled: false },
    { day: "Saturday", value: "12:00 PM–3:00 PM", enabled: true },
    { day: "Sunday", value: "Unavailable", enabled: false },
  ];

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_19rem]">
      <div className="overflow-hidden rounded-2xl border border-line bg-background shadow-sm">
        <div className="border-b border-line bg-surface/60 px-4 py-4 sm:px-5">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-brand">Profile settings</p>
          <h3 className="type-wide mt-1 text-xl font-black text-ink">Meetup preferences</h3>
          <p className="mt-1 text-sm text-muted">Set this up before publishing your first listing. You can change it anytime.</p>
        </div>

        <div className="space-y-7 p-4 sm:p-5">
          <fieldset>
            <legend className="font-bold text-ink">Places you&apos;re comfortable meeting</legend>
            <p className="mt-1 text-sm text-muted">Choose at least one school-approved location.</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {SPOTS.map((spot, index) => (
                <label key={spot.id} className="flex cursor-pointer items-start gap-3 rounded-xl border border-line p-3">
                  <input type="checkbox" defaultChecked={index < 2} className="mt-1 size-4 accent-[var(--brand)]" />
                  <span>
                    <span className="block text-sm font-bold text-ink">{spot.name}</span>
                    <span className="block text-xs leading-5 text-muted">{spot.detail}</span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          <fieldset>
            <legend className="font-bold text-ink">Your usual weekly availability</legend>
            <p className="mt-1 text-sm text-muted">Unavailable days will never appear as buyer choices.</p>
            <div className="mt-3 divide-y divide-line rounded-xl border border-line">
              {windows.map((window) => (
                <div key={window.day} className="flex items-center gap-3 px-3 py-3">
                  <span className={`size-2 rounded-full ${window.enabled ? "bg-brand" : "bg-line"}`} aria-hidden="true" />
                  <span className="w-24 text-sm font-bold text-ink">{window.day}</span>
                  <span className={`min-w-0 flex-1 text-sm ${window.enabled ? "text-ink" : "text-muted"}`}>{window.value}</span>
                  <button type="button" className="text-sm font-bold text-ink underline underline-offset-4">Edit</button>
                </div>
              ))}
            </div>
            <button type="button" className="btn btn-secondary mt-3 w-full">Add another time window</button>
          </fieldset>

          <div className="rounded-xl border border-line bg-surface/60 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-bold text-ink">Temporary changes</p>
                <p className="mt-1 text-sm leading-5 text-muted">Add a one-time opening or block a day without changing your normal week.</p>
              </div>
              <button type="button" className="btn btn-secondary btn-sm shrink-0">Add</button>
            </div>
            <p className="mt-3 rounded-lg bg-background px-3 py-2 text-sm text-ink">Tomorrow · Available 12:00–2:00 PM</p>
          </div>

          <button type="button" className="btn btn-primary w-full">Save meetup preferences</button>
        </div>
      </div>

      <aside className="space-y-4">
        <div className="rounded-2xl border border-line bg-surface/60 p-4">
          <p className="font-bold text-ink">Required before selling</p>
          <ul className="mt-3 space-y-2 text-sm leading-5 text-muted">
            <li>✓ At least one approved location</li>
            <li>✓ At least one availability window</li>
            <li>✓ School time zone applied</li>
          </ul>
        </div>
        <div className="rounded-2xl border border-line p-4">
          <p className="font-bold text-ink">You stay in control</p>
          <p className="mt-2 text-sm leading-6 text-muted">These windows only create suggestions. A buyer&apos;s request is not confirmed until you accept it.</p>
        </div>
      </aside>
    </div>
  );
}

function SellerResponseMock() {
  const [state, setState] = useState<"waiting" | "change" | "accepted">("waiting");
  const [lateBy, setLateBy] = useState<number | null>(null);

  if (state === "accepted") {
    return (
      <div className="mx-auto max-w-2xl overflow-hidden rounded-2xl border border-line bg-background shadow-sm">
        <div className="bg-[var(--brand-soft)] px-5 py-6 text-center">
          <span className="mx-auto grid size-12 place-items-center rounded-full bg-brand text-xl font-black text-white">✓</span>
          <h3 className="type-wide mt-3 text-2xl font-black text-ink">Meetup confirmed</h3>
          <p className="mt-1 text-sm text-muted">Jordan has been notified. The 72-hour exchange window starts now.</p>
        </div>
        <div className="grid gap-4 p-5 sm:grid-cols-2">
          <div className="rounded-xl border border-line p-4">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">When</p>
            <p className="mt-2 font-bold text-ink">Today, Oct 12 · 5:30 PM</p>
            <p className="mt-1 text-sm text-muted">Both people will receive a reminder.</p>
          </div>
          <div className="rounded-xl border border-line p-4">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Where</p>
            <p className="mt-2 font-bold text-ink">McKeldin Library</p>
            <p className="mt-1 text-sm text-muted">Main entrance · by the security desk</p>
          </div>
        </div>
        <div className="border-t border-line px-5 py-4">
          <p className="font-bold text-ink">Plans changed?</p>
          <p className="mt-1 text-sm text-muted">Send a quick update without opening chat.</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {[5, 10, 15].map((minutes) => (
              <button
                key={minutes}
                type="button"
                onClick={() => setLateBy(minutes)}
                aria-pressed={lateBy === minutes}
                className={`rounded-full border px-3 py-2 text-sm font-bold ${lateBy === minutes ? "border-brand bg-[var(--brand-soft)] text-brand" : "border-line text-ink"}`}
              >
                {minutes} min late
              </button>
            ))}
            <button type="button" className="rounded-full border border-line px-3 py-2 text-sm font-bold text-ink">I&apos;m here</button>
            <button type="button" className="rounded-full border border-line px-3 py-2 text-sm font-bold text-ink">Reschedule</button>
          </div>
          {lateBy && (
            <div className="mt-3 rounded-lg bg-surface px-3 py-2 text-sm leading-5 text-ink">
              Jordan will see: <span className="font-bold">Maya is running about {lateBy} minutes late.</span>
              <button type="button" onClick={() => setLateBy(null)} className="ml-2 font-bold underline underline-offset-4">Undo</button>
            </div>
          )}
        </div>
        <div className="border-t border-line px-5 py-4">
          <p className="text-sm leading-6 text-muted">Chat remains available for delays or last-minute details, but the agreed meetup stays visible on the deal.</p>
          <button type="button" onClick={() => { setState("waiting"); setLateBy(null); }} className="btn btn-secondary mt-3 w-full">Reset mock</button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl overflow-hidden rounded-2xl border border-line bg-background shadow-sm">
      <div className="border-b border-line bg-surface/60 px-5 py-4">
        <div className="flex items-start gap-3">
          <div className="size-14 shrink-0 rounded-lg bg-cover bg-center" style={{ backgroundImage: "url(/demo-listings/real/tan-washed-chore-jacket.jpg)" }} aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-brand">Purchase request</p>
            <p className="truncate font-bold text-ink">Jordan wants to buy your jacket</p>
            <p className="text-sm text-muted">$36 · Requested just now</p>
          </div>
          <span className="rounded-full bg-[var(--brand-soft)] px-2.5 py-1 text-xs font-bold text-brand">Action needed</span>
        </div>
      </div>

      <div className="p-5">
        <p className="font-bold text-ink">Jordan proposed</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-line p-4">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Location</p>
            <p className="mt-2 font-bold text-ink">McKeldin Library</p>
            <p className="mt-1 text-sm text-muted">Main entrance · by the security desk</p>
          </div>
          <div className="rounded-xl border border-line p-4">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Time</p>
            <p className="mt-2 font-bold text-ink">Today · 5:30 PM</p>
            <p className="mt-1 text-sm text-muted">Matches your usual Monday availability</p>
          </div>
        </div>

        {state === "change" ? (
          <div className="mt-4 rounded-xl border border-line bg-surface/60 p-4">
            <p className="font-bold text-ink">Suggest a different available time</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {["6:00 PM today", "6:30 PM today", "4:30 PM tomorrow"].map((option) => (
                <button key={option} type="button" className="rounded-full border border-line bg-background px-3 py-2 text-sm font-bold text-ink">{option}</button>
              ))}
            </div>
            <div className="mt-3 flex gap-2">
              <button type="button" onClick={() => setState("waiting")} className="btn btn-secondary flex-1">Back</button>
              <button type="button" className="btn btn-primary flex-1">Send change</button>
            </div>
          </div>
        ) : (
          <div className="mt-5 grid gap-2 sm:grid-cols-2">
            <button type="button" onClick={() => setState("accepted")} className="btn btn-primary">Accept purchase and meetup</button>
            <button type="button" onClick={() => setState("change")} className="btn btn-secondary">Suggest another time</button>
            <button type="button" className="btn btn-secondary sm:col-span-2">Decline purchase request</button>
          </div>
        )}
        <p className="mt-4 text-center text-xs text-muted">Answer within 24 hours. The item stays available until you accept.</p>
      </div>
    </div>
  );
}

export function MeetupSchedulerMock() {
  const [view, setView] = useState<"seller" | "buyer" | "response">("buyer");
  const [spotId, setSpotId] = useState("mckeldin");
  const [dayId, setDayId] = useState("today");
  const [time, setTime] = useState("5:30 PM");
  const [confirmed, setConfirmed] = useState(false);

  const spot = useMemo(() => SPOTS.find((item) => item.id === spotId) ?? SPOTS[0], [spotId]);
  const day = useMemo(() => DAYS.find((item) => item.id === dayId) ?? DAYS[0], [dayId]);

  function chooseDay(nextDay: Day) {
    setDayId(nextDay.id);
    setTime(nextDay.times[0]);
    setConfirmed(false);
  }

  return (
    <div>
      <div className="mb-5 inline-flex rounded-xl bg-surface p-1" role="group" aria-label="Meetup mock view">
        <button type="button" onClick={() => setView("seller")} aria-pressed={view === "seller"} className={`rounded-lg px-4 py-2 text-sm font-bold ${view === "seller" ? "bg-background text-ink shadow-sm" : "text-muted"}`}>Seller setup</button>
        <button type="button" onClick={() => setView("buyer")} aria-pressed={view === "buyer"} className={`rounded-lg px-4 py-2 text-sm font-bold ${view === "buyer" ? "bg-background text-ink shadow-sm" : "text-muted"}`}>Buyer flow</button>
        <button type="button" onClick={() => setView("response")} aria-pressed={view === "response"} className={`rounded-lg px-4 py-2 text-sm font-bold ${view === "response" ? "bg-background text-ink shadow-sm" : "text-muted"}`}>Seller response</button>
      </div>

      {view === "seller" ? <SellerPreferencesMock /> : view === "response" ? <SellerResponseMock /> : <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_19rem]">
      <div className="overflow-hidden rounded-2xl border border-line bg-background shadow-sm">
        <div className="border-b border-line bg-surface/60 px-4 py-4 sm:px-5">
          <div className="flex items-start gap-3">
            <div
              className="size-14 shrink-0 rounded-lg bg-cover bg-center"
              style={{ backgroundImage: "url(/demo-listings/real/tan-washed-chore-jacket.jpg)" }}
              aria-hidden="true"
            />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-brand">Buy now</p>
              <p className="truncate font-bold text-ink">Tan washed canvas chore jacket</p>
              <p className="text-sm text-muted">$36 · Choose a meetup before sending your request</p>
            </div>
            <span className="rounded-full bg-[var(--brand-soft)] px-2.5 py-1 text-xs font-bold text-brand">
              Step 1 of 2
            </span>
          </div>

          <ol className="mt-4 grid grid-cols-3 gap-2 text-xs font-bold" aria-label="Meetup steps">
            {["Place", "Time", "Meet"].map((label, index) => (
              <li key={label} className="flex items-center gap-1.5 text-ink">
                <span className="grid size-5 shrink-0 place-items-center rounded-full bg-ink text-[10px] text-white">
                  {index + 1}
                </span>
                {label}
              </li>
            ))}
          </ol>
        </div>

        <div className="space-y-7 p-4 sm:p-5">
          <fieldset>
            <legend className="type-wide text-lg font-black text-ink">Where should you meet?</legend>
            <p className="mt-1 text-sm text-muted">Maya chose these approved UMD locations.</p>
            <div className="mt-3 grid gap-2">
              {SPOTS.map((item) => {
                const selected = item.id === spotId;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => {
                      setSpotId(item.id);
                      setConfirmed(false);
                    }}
                    aria-pressed={selected}
                    className={`rounded-xl border p-3 text-left transition ${
                      selected ? "border-ink bg-surface ring-1 ring-ink" : "border-line hover:border-ink/50"
                    }`}
                  >
                    <span className="flex items-start gap-3">
                      <span
                        className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-full border ${
                          selected ? "border-ink bg-ink" : "border-line"
                        }`}
                        aria-hidden="true"
                      >
                        {selected && <span className="size-1.5 rounded-full bg-white" />}
                      </span>
                      <span className="min-w-0">
                        <span className="block font-bold text-ink">
                          {item.name} {item.indoor && <span className="font-medium text-muted">· Indoors</span>}
                        </span>
                        <span className="mt-0.5 block text-sm text-muted">{item.detail}</span>
                        <span className="mt-1 block text-xs font-medium text-brand">{item.note}</span>
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </fieldset>

          <fieldset>
            <legend className="type-wide text-lg font-black text-ink">When works for you?</legend>
            <p className="mt-1 text-sm text-muted">Only times that match Maya&apos;s availability are shown.</p>
            <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
              {DAYS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => chooseDay(item)}
                  aria-pressed={item.id === dayId}
                  className={`min-w-24 rounded-lg border px-3 py-2 text-left ${
                    item.id === dayId ? "border-ink bg-ink text-white" : "border-line text-ink"
                  }`}
                >
                  <span className="block text-sm font-bold">{item.label}</span>
                  <span className={`block text-xs ${item.id === dayId ? "text-white/70" : "text-muted"}`}>
                    {item.date}
                  </span>
                </button>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {day.times.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => {
                    setTime(item);
                    setConfirmed(false);
                  }}
                  aria-pressed={item === time}
                  className={`rounded-full border px-3 py-2 text-sm font-bold ${
                    item === time ? "border-brand bg-[var(--brand-soft)] text-brand" : "border-line text-ink"
                  }`}
                >
                  {item}
                </button>
              ))}
            </div>
            <button type="button" className="mt-3 text-sm font-bold text-ink underline underline-offset-4">
              None of these work? Propose another time
            </button>
          </fieldset>

          {confirmed ? (
            <div className="rounded-xl border border-brand bg-[var(--brand-soft)] p-4">
              <p className="font-bold text-brand">Purchase request sent to Maya</p>
              <p className="mt-1 text-sm leading-6 text-ink">
                {spot.name} · {day.label}, {day.date} at {time}
              </p>
              <p className="mt-1 text-xs text-muted">Maya can accept the purchase and meetup together, or suggest a different time.</p>
            </div>
          ) : (
            <button type="button" onClick={() => setConfirmed(true)} className="btn btn-primary w-full">
              Send purchase request
            </button>
          )}
        </div>
      </div>

      <aside className="space-y-4">
        <div className="rounded-2xl border border-line bg-surface/60 p-4">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted">Your meetup</p>
          <p className="mt-3 font-bold text-ink">{spot.name}</p>
          <p className="text-sm text-muted">{spot.detail}</p>
          <div className="my-3 border-t border-line" />
          <p className="font-bold text-ink">{day.label}, {day.date}</p>
          <p className="text-sm text-muted">{time}</p>
        </div>

        <div className="rounded-2xl border border-line p-4">
          <p className="font-bold text-ink">How the times appeared</p>
          <ul className="mt-2 space-y-2 text-sm leading-5 text-muted">
            <li>Seller preference: weekdays, 4–7 PM</li>
            <li>Location is open and approved</li>
            <li>Slot is inside the 72-hour window</li>
            <li>Already-booked times are removed</li>
          </ul>
          <p className="mt-3 rounded-lg bg-surface px-3 py-2 text-xs leading-5 text-muted">
            Preferences create suggestions, not obligations. Either person can propose a different time.
          </p>
        </div>
      </aside>
      </div>}
    </div>
  );
}
