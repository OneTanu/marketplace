"use client";

import { useEffect, useMemo, useState } from "react";

import type { components } from "@/lib/api/schema";
import { getMeetupOptions } from "@/lib/deals";
import { dayKey, formatTime, formatWeekdayDate } from "@/lib/time";
import { MeetingSpotName } from "@/components/deals/meeting-spot-name";

type MeetupOptions = components["schemas"]["MeetupOptions"];

export type MeetupSelection = {
  meetingSpotId: number | null;
  startsAt: string[];
  configured: boolean;
  loading: boolean;
};

export function MeetupPicker({
  listingId,
  allowTwo,
  onChange,
}: {
  listingId: number;
  allowTwo: boolean;
  onChange: (selection: MeetupSelection) => void;
}) {
  const [options, setOptions] = useState<MeetupOptions | null>();
  const [spotId, setSpotId] = useState<number | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [day, setDay] = useState("");

  useEffect(() => {
    let active = true;
    getMeetupOptions(listingId)
      .then((data) => {
        if (!active) return;
        setOptions(data);
        setSpotId(data.meeting_spots[0]?.id ?? null);
        setDay(data.slots[0] ? dayKey(data.slots[0].starts_at) : "");
      })
      .catch(() => active && setOptions(null));
    return () => {
      active = false;
    };
  }, [listingId]);

  useEffect(() => {
    onChange({
      meetingSpotId: spotId,
      startsAt: selected,
      configured: Boolean(options?.seller_configured),
      loading: options === undefined,
    });
  }, [onChange, options, selected, spotId]);

  const days = useMemo(() => {
    const grouped = new Map<string, string[]>();
    for (const slot of options?.slots ?? []) {
      const key = dayKey(slot.starts_at);
      grouped.set(key, [...(grouped.get(key) ?? []), slot.starts_at]);
    }
    return [...grouped.entries()];
  }, [options]);

  function toggleTime(value: string) {
    setSelected((current) => {
      if (current.includes(value)) return current.filter((item) => item !== value);
      if (!allowTwo) return [value];
      return [...current, value].slice(-2);
    });
  }

  if (options === undefined) {
    return <div className="mt-3 h-36 animate-pulse rounded-xl bg-surface" aria-label="Loading meetup options" />;
  }
  if (options === null) {
    return <p className="mt-3 rounded-lg bg-surface p-3 text-sm text-muted">Couldn&apos;t load meetup options. Try again.</p>;
  }
  if (!options.seller_configured) {
    return <p className="mt-3 rounded-lg border border-line bg-surface p-3 text-sm leading-6 text-muted">This seller hasn&apos;t set meetup times yet. Agree on a campus spot and time in chat.</p>;
  }

  return (
    <div className="mt-4 space-y-4 border-t border-line pt-4">
      <fieldset>
        <legend className="text-sm font-bold">Choose a safe campus location</legend>
        <div className="mt-2 grid gap-2">
          {options.meeting_spots.map((spot) => (
            <button key={spot.id} type="button" onClick={() => setSpotId(spot.id)} aria-pressed={spot.id === spotId} className={`rounded-lg border px-3 py-2 text-left text-sm ${spot.id === spotId ? "border-ink bg-surface ring-1 ring-ink" : "border-line"}`}>
              <span className="block font-bold"><MeetingSpotName spot={spot} /></span>
              <span className="block text-xs leading-5 text-muted">{spot.directions}</span>
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend className="text-sm font-bold">{allowTwo ? "Choose up to two times" : "Choose a time"}</legend>
        {allowTwo && <p className="mt-1 text-xs text-muted">A second option helps if price negotiation takes time.</p>}
        <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
          {days.map(([key, slots]) => (
            <button key={key} type="button" onClick={() => setDay(key)} aria-pressed={day === key} className={`shrink-0 rounded-lg border px-3 py-2 text-sm font-bold ${day === key ? "border-ink bg-ink text-white" : "border-line"}`}>
              {formatWeekdayDate(slots[0])}
            </button>
          ))}
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          {(days.find(([key]) => key === day)?.[1] ?? []).map((slot) => (
            <button key={slot} type="button" onClick={() => toggleTime(slot)} aria-pressed={selected.includes(slot)} className={`rounded-full border px-3 py-2 text-sm font-bold ${selected.includes(slot) ? "border-brand bg-[var(--brand-soft)] text-brand" : "border-line"}`}>
              {formatTime(slot)}
            </button>
          ))}
        </div>
      </fieldset>
    </div>
  );
}
