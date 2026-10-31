"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { getMeetupPreferences, saveMeetupPreferences } from "@/lib/deals";
import { getCurrentUser } from "@/lib/platform";
import { MeetingSpotName } from "@/components/deals/meeting-spot-name";

type MeetingSpot = components["schemas"]["MeetingSpot"];
type Override = components["schemas"]["AvailabilityOverrideRequest"];

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

type TimeRange = { start: string; end: string };
type WindowState = { enabled: boolean; ranges: TimeRange[] };

const DEFAULT_RANGE: TimeRange = { start: "16:00", end: "19:00" };

const blankWindows = () =>
  DAYS.map<WindowState>(() => ({ enabled: false, ranges: [DEFAULT_RANGE] }));

// Suggest the next range two hours after the day's last one, kept within the day.
function nextRange(ranges: TimeRange[]): TimeRange {
  const last = ranges.at(-1);
  if (!last) return DEFAULT_RANGE;
  const [hours, minutes] = last.end.split(":").map(Number);
  const start = Math.min(hours + 1, 22);
  const pad = (value: number) => String(value).padStart(2, "0");
  return { start: `${pad(start)}:${pad(minutes)}`, end: `${pad(start + 1)}:${pad(minutes)}` };
}

export function MeetupPreferences() {
  const [spots, setSpots] = useState<MeetingSpot[]>([]);
  const [selectedSpots, setSelectedSpots] = useState<number[]>([]);
  const [windows, setWindows] = useState<WindowState[]>(blankWindows);
  const [overrides, setOverrides] = useState<Override[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const user = await getCurrentUser();
        if (!user?.school) throw new Error("Your account is not connected to a school.");
        const [preference, available] = await Promise.all([
          getMeetupPreferences(),
          api.GET("/api/schools/{slug}/meeting-spots/", {
            params: { path: { slug: user.school.slug } },
          }),
        ]);
        if (!active) return;
        setSpots(available.data ?? []);
        setSelectedSpots(preference.meeting_spots.map((spot) => spot.id));
        setOverrides(
          preference.availability_overrides.map((item) => ({
            date: item.date,
            is_unavailable: item.is_unavailable,
            start_time: item.start_time,
            end_time: item.end_time,
          })),
        );
        const next = blankWindows();
        for (const window of preference.availability_windows) {
          const range = { start: window.start_time.slice(0, 5), end: window.end_time.slice(0, 5) };
          const day = next[window.weekday];
          next[window.weekday] = day.enabled
            ? { enabled: true, ranges: [...day.ranges, range] }
            : { enabled: true, ranges: [range] };
        }
        setWindows(next);
      } catch (caught) {
        if (active) setError(caught instanceof Error ? caught.message : "Couldn't load meetup preferences.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, []);

  function toggleSpot(id: number) {
    setSelectedSpots((current) =>
      current.includes(id) ? current.filter((spotId) => spotId !== id) : [...current, id],
    );
    setSaved(false);
  }

  function updateDay(index: number, update: (day: WindowState) => WindowState) {
    setWindows((current) =>
      current.map((window, position) => (position === index ? update(window) : window)),
    );
    setSaved(false);
  }

  function updateRange(index: number, rangeIndex: number, patch: Partial<TimeRange>) {
    updateDay(index, (day) => ({
      ...day,
      ranges: day.ranges.map((range, position) =>
        position === rangeIndex ? { ...range, ...patch } : range,
      ),
    }));
  }

  function removeRange(index: number, rangeIndex: number) {
    updateDay(index, (day) => {
      const ranges = day.ranges.filter((_, position) => position !== rangeIndex);
      return ranges.length ? { ...day, ranges } : { enabled: false, ranges: [DEFAULT_RANGE] };
    });
  }

  async function save() {
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      await saveMeetupPreferences({
        meeting_spot_ids: selectedSpots,
        windows: windows.flatMap((window, weekday) =>
          window.enabled
            ? window.ranges.map((range) => ({ weekday, start_time: range.start, end_time: range.end }))
            : [],
        ),
        overrides,
      });
      setSaved(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Couldn't save meetup preferences.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <main className="mx-auto min-h-[70vh] max-w-3xl animate-pulse px-4 py-10 sm:px-6"><div className="h-96 rounded-2xl bg-surface" /></main>;
  }

  return (
    <main className="mx-auto min-h-[70vh] max-w-3xl px-4 py-8 pb-28 sm:px-6 sm:py-10 desktop:pb-12">
      <Link href="/profile" className="text-sm font-bold text-muted hover:text-ink">← Back to profile</Link>
      <div className="mt-5">
        <p className="text-sm font-bold uppercase tracking-[0.14em] text-signal">Seller setup</p>
        <h1 className="type-wide mt-1 text-3xl font-black">Meetup preferences</h1>
        <p className="mt-2 max-w-2xl leading-6 text-muted">Buyers only see approved campus locations and times that fit your schedule. You confirm every request before a meetup becomes official.</p>
      </div>

      <section className="mt-8 rounded-2xl border border-line bg-background p-5">
        <h2 className="text-lg font-bold">Preferred campus locations</h2>
        <p className="mt-1 text-sm text-muted">Choose at least one place where you are comfortable exchanging an item.</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {spots.map((spot) => (
            <label key={spot.id} className="flex cursor-pointer items-start gap-3 rounded-xl border border-line p-4">
              <input type="checkbox" checked={selectedSpots.includes(spot.id)} onChange={() => toggleSpot(spot.id)} className="mt-1 size-4 accent-[var(--brand)]" />
              <span>
                <span className="block font-bold"><MeetingSpotName spot={spot} /></span>
                <span className="mt-1 block text-sm leading-5 text-muted">{spot.directions}</span>
                {spot.safety_note && <span className="mt-1 block text-xs text-brand">{spot.safety_note}</span>}
              </span>
            </label>
          ))}
        </div>
      </section>

      <section className="mt-5 rounded-2xl border border-line bg-background p-5">
        <h2 className="text-lg font-bold">Usual weekly availability</h2>
        <p className="mt-1 text-sm text-muted">Turn off days when you normally cannot meet, or add more than one time range for a day, like between classes and after practice.</p>
        <div className="mt-4 divide-y divide-line rounded-xl border border-line">
          {DAYS.map((day, index) => (
            <div key={day} className="grid gap-3 px-3 py-3 sm:grid-cols-[7rem_1fr] sm:items-start">
              <label className="flex items-center gap-2 font-bold sm:h-10">
                <input type="checkbox" checked={windows[index].enabled} onChange={(event) => updateDay(index, (current) => ({ ...current, enabled: event.target.checked }))} className="size-4 accent-[var(--brand)]" />
                {day}
              </label>
              {windows[index].enabled ? (
                <div className="space-y-2">
                  {windows[index].ranges.map((range, rangeIndex) => (
                    <div key={rangeIndex} className="flex items-center gap-2">
                      <input type="time" value={range.start} onChange={(event) => updateRange(index, rangeIndex, { start: event.target.value })} className="field h-10 min-w-0 flex-1 px-3" aria-label={`${day} start time ${rangeIndex + 1}`} />
                      <span className="text-sm text-muted">to</span>
                      <input type="time" value={range.end} onChange={(event) => updateRange(index, rangeIndex, { end: event.target.value })} className="field h-10 min-w-0 flex-1 px-3" aria-label={`${day} end time ${rangeIndex + 1}`} />
                      <button type="button" onClick={() => removeRange(index, rangeIndex)} aria-label={`Remove ${day} time range ${rangeIndex + 1}`} className="grid size-10 shrink-0 place-items-center rounded-lg text-muted hover:bg-surface hover:text-ink">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="size-4" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
                      </button>
                    </div>
                  ))}
                  <button type="button" onClick={() => updateDay(index, (current) => ({ ...current, ranges: [...current.ranges, nextRange(current.ranges)] }))} className="text-sm font-bold text-brand hover:underline">
                    + Add another time
                  </button>
                </div>
              ) : (
                <p className="text-sm text-muted">Unavailable</p>
              )}
            </div>
          ))}
        </div>
      </section>

      {error && <p role="alert" className="mt-4 text-sm text-[var(--danger)]">{error}</p>}
      {saved && <p role="status" className="mt-4 text-sm font-bold text-brand">Meetup preferences saved.</p>}
      <button type="button" onClick={save} disabled={saving} className="btn btn-primary mt-5 w-full">{saving ? "Saving…" : "Save meetup preferences"}</button>
    </main>
  );
}
