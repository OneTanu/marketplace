"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ModeratorsOnly } from "@/components/moderation/queue";
import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { getModerationStats, type ModerationStats, type StatsQuery } from "@/lib/moderation";

type CountRow = components["schemas"]["CountRow"];
type School = components["schemas"]["School"];

const RANGES: StatsQuery["days"][] = [7, 30, 90];

function duration(hours: number | null) {
  if (hours === null) return "—";
  if (hours < 1) return `${Math.max(1, Math.round(hours * 60))} min`;
  if (hours < 48) return `${hours.toFixed(hours < 10 ? 1 : 0)} h`;
  return `${(hours / 24).toFixed(1)} days`;
}

function Tile({ label, value, note }: { label: string; value: string | number; note?: string }) {
  return (
    <div className="rounded-xl border border-line p-4">
      <p className="text-sm text-muted">{label}</p>
      <p className="type-wide mt-1 text-3xl font-black">{value}</p>
      {note && <p className="mt-1 text-xs text-muted">{note}</p>}
    </div>
  );
}

/** A sorted, single-colour bar list. Each value is printed beside its bar, so the numbers
 * never depend on reading the bar length or colour. */
function BarList({ title, rows, empty }: { title: string; rows: CountRow[]; empty: string }) {
  const max = Math.max(1, ...rows.map((row) => row.count));
  const total = rows.reduce((sum, row) => sum + row.count, 0);
  return (
    <section aria-label={title} className="rounded-xl border border-line p-4">
      <h2 className="font-black">{title}</h2>
      {rows.length === 0 ? (
        <p className="mt-2 text-sm text-muted">{empty}</p>
      ) : (
        <ul className="mt-3 space-y-2.5">
          {rows.map((row) => (
            <li key={row.key} title={`${row.label}: ${row.count} (${Math.round((row.count / total) * 100)}%)`} className="text-sm">
              <div className="flex items-baseline justify-between gap-3">
                <span className="truncate">{row.label}</span>
                <span className="shrink-0 font-bold tabular-nums">{row.count}</span>
              </div>
              <div className="mt-1 h-2 rounded-full bg-surface">
                <div className="h-2 rounded-full bg-brand" style={{ width: `${(row.count / max) * 100}%` }} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function ModerationStatsView() {
  const [query, setQuery] = useState<StatsQuery>({ days: 30 });
  const [stats, setStats] = useState<ModerationStats | null>();
  const [denied, setDenied] = useState("");
  const [schools, setSchools] = useState<School[]>([]);

  useEffect(() => {
    let active = true;
    api.GET("/api/schools/").then(({ data }) => active && data && setSchools(data));
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    getModerationStats(query)
      .then((data) => active && setStats(data))
      .catch((caught) => {
        if (!active) return;
        setStats(null);
        setDenied(caught instanceof Error ? caught.message : "Only moderators can see moderation stats.");
      });
    return () => {
      active = false;
    };
  }, [query]);

  if (stats === null) return <ModeratorsOnly message={denied} />;

  return (
    <main className="mx-auto min-h-[70vh] max-w-5xl px-4 py-8 pb-28 sm:px-6 desktop:pb-12">
      <Link href="/moderation" className="text-sm font-bold text-muted hover:text-ink">← Moderation queue</Link>
      <h1 className="type-wide mt-3 text-3xl font-black">Moderation stats</h1>

      <div className="mt-5 flex flex-wrap items-center gap-2" aria-label="Filters">
        <div className="flex rounded-lg bg-surface p-1 text-sm" role="group" aria-label="Time range">
          {RANGES.map((days) => (
            <button key={days} type="button" onClick={() => setQuery((current) => ({ ...current, days }))} aria-pressed={query.days === days} className={`rounded-md px-3 py-1.5 font-semibold ${query.days === days ? "bg-background shadow-sm" : "text-muted"}`}>
              Last {days} days
            </button>
          ))}
        </div>
        <select aria-label="School" value={query.school ?? ""} onChange={(event) => setQuery((current) => ({ ...current, school: event.target.value }))} className="field h-10 w-auto px-3 text-sm">
          <option value="">Every school</option>
          {schools.map((school) => <option key={school.slug} value={school.slug}>{school.short_name}</option>)}
        </select>
      </div>

      {stats === undefined ? (
        <div className="mt-6 grid animate-pulse grid-cols-2 gap-3 sm:grid-cols-3">{[0, 1, 2, 3, 4, 5].map((i) => <div key={i} className="h-24 rounded-xl bg-surface" />)}</div>
      ) : (
        <>
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Tile label="Cases opened" value={stats.cases_opened} note={`${stats.reports} ${stats.reports === 1 ? "report" : "reports"}`} />
            <Tile label="Cases resolved" value={stats.cases_resolved} />
            <Tile label="Open now" value={stats.open_now} note={`${stats.urgent_open} urgent`} />
            <Tile label="Median time to first action" value={duration(stats.median_hours_to_first_action)} note="For cases opened in this range" />
            <Tile label="Median time to resolve" value={duration(stats.median_hours_to_resolve)} />
            <Tile label="Appeals" value={stats.appeals_filed} note={`${stats.appeals_overturned} overturned · ${stats.appeals_upheld} upheld · ${stats.appeals_pending} pending`} />
          </div>

          <div className="mt-6 grid gap-3 lg:grid-cols-3">
            <BarList title="Reports by reason" rows={stats.reports_by_reason} empty="No reports in this range." />
            <BarList title="Reports by school" rows={stats.reports_by_school} empty="No reports in this range." />
            <BarList title="Outcomes" rows={stats.outcomes} empty="No decisions in this range." />
          </div>

          <p className="mt-8 text-sm text-muted">The lists below are signals for a closer look, not proof. Review each case before acting.</p>
          <div className="mt-3 grid gap-3 lg:grid-cols-2">
            <section aria-label="Repeat offenders" className="rounded-xl border border-line p-4">
              <h2 className="font-black">Repeat offenders</h2>
              <p className="text-xs text-muted">Two or more warnings, restrictions, removals, suspensions or bans in the last 90 days.</p>
              {stats.repeat_offenders.length === 0 ? (
                <p className="mt-2 text-sm text-muted">None.</p>
              ) : (
                <table className="mt-3 w-full text-sm">
                  <thead><tr className="text-left text-xs text-muted"><th className="font-semibold">Student</th><th className="text-right font-semibold">Consequences</th></tr></thead>
                  <tbody>
                    {stats.repeat_offenders.map((row) => (
                      <tr key={row.user.id} className="border-t border-line">
                        <td className="py-2"><Link href={`/users/${row.user.username}`} className="font-semibold hover:underline">@{row.user.username}</Link></td>
                        <td className="py-2 text-right font-bold tabular-nums">{row.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
            <section aria-label="Possible false reporters" className="rounded-xl border border-line p-4">
              <h2 className="font-black">Possible false reporters</h2>
              <p className="text-xs text-muted">Three or more reviewed reports, with a quarter or fewer leading to action.</p>
              {stats.possible_false_reporters.length === 0 ? (
                <p className="mt-2 text-sm text-muted">None.</p>
              ) : (
                <table className="mt-3 w-full text-sm">
                  <thead><tr className="text-left text-xs text-muted"><th className="font-semibold">Reporter</th><th className="text-right font-semibold">Led to action</th></tr></thead>
                  <tbody>
                    {stats.possible_false_reporters.map((row) => (
                      <tr key={row.user.id} className="border-t border-line">
                        <td className="py-2"><Link href={`/users/${row.user.username}`} className="font-semibold hover:underline">@{row.user.username}</Link></td>
                        <td className="py-2 text-right tabular-nums"><span className="font-bold">{row.upheld}</span> of {row.reviewed}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          </div>
        </>
      )}
    </main>
  );
}
