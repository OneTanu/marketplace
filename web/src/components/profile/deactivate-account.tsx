"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { deactivateAccount, getDeactivationPreview } from "@/lib/account";
import type { components } from "@/lib/api/schema";

type Preview = components["schemas"]["DeactivationPreview"];

const REASONS = [
  "Graduating or leaving campus",
  "Taking a break",
  "Not finding what I need",
  "Safety or privacy concerns",
  "Something else",
];

/** Close your own account: what happens, deals to settle first, then a password check. */
export function DeactivateAccount() {
  const router = useRouter();
  const [preview, setPreview] = useState<Preview | null>();
  const [password, setPassword] = useState("");
  const [reason, setReason] = useState("");
  const [understood, setUnderstood] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getDeactivationPreview()
      .then((data) => active && setPreview(data))
      .catch(() => active && setPreview(null));
    return () => {
      active = false;
    };
  }, []);

  async function submit() {
    setWorking(true);
    setError("");
    try {
      await deactivateAccount(password, reason);
      router.push("/account/deactivated");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Your account couldn't be deactivated. Try again.");
      setWorking(false);
    }
  }

  if (preview === undefined) return <main className="mx-auto min-h-[70vh] max-w-2xl animate-pulse px-4 py-10"><div className="h-72 rounded-2xl bg-surface" /></main>;
  if (preview === null) return <main className="mx-auto grid min-h-[70vh] max-w-xl place-items-center px-4 text-center"><div><h1 className="type-wide text-3xl font-black">Log in to manage your account</h1><Link href="/account/login" className="btn btn-primary mt-6">Log in</Link></div></main>;

  const blocked = preview.blockers.length > 0;

  return (
    <main className="mx-auto min-h-[70vh] max-w-2xl px-4 py-8 pb-28 sm:px-6 desktop:pb-12">
      <Link href="/profile/standing" className="text-sm font-bold text-muted hover:text-ink">← Account status</Link>
      <h1 className="type-wide mt-4 text-3xl font-black">Deactivate your account</h1>
      <p className="mt-2 text-muted">Taking your thrift offline. You can come back any time by logging in again.</p>

      <section aria-labelledby="happens-heading" className="mt-6 rounded-xl border border-line p-4 text-sm">
        <h2 id="happens-heading" className="font-bold">What happens</h2>
        <ul className="mt-2 list-disc space-y-1.5 pl-5 text-muted">
          <li>You&apos;re signed out on every device, and your profile is hidden.</li>
          <li>
            {preview.listings_to_hide === 0
              ? "You have no listings to hide."
              : `Your ${preview.listings_to_hide} available ${preview.listings_to_hide === 1 ? "listing is" : "listings are"} hidden. They come back if you return.`}
          </li>
          <li>
            {preview.open_deals === 0
              ? "You have no open requests or deals."
              : `Your ${preview.open_deals} open ${preview.open_deals === 1 ? "request or deal is" : "requests and deals are"} withdrawn, and the other students are told.`}
          </li>
          <li>Your conversations stay in the other students&apos; inboxes, but they can&apos;t reply.</li>
          <li>Completed deals, reviews, and any reports or moderation records are kept.</li>
        </ul>
      </section>

      {blocked ? (
        <section aria-labelledby="blockers-heading" className="mt-6 rounded-xl border border-[var(--danger)] p-4 text-sm">
          <h2 id="blockers-heading" className="font-bold">Settle these deals first</h2>
          <p className="mt-1 text-muted">A handoff that someone already confirmed, or one a moderator is reviewing, can&apos;t be withdrawn. Confirm it, or wait for the review to finish.</p>
          <ul className="mt-3 space-y-2">
            {preview.blockers.map((deal) => (
              <li key={deal.id} className="flex items-center justify-between gap-3 rounded-lg bg-surface p-3">
                <span><span className="font-semibold">{deal.listing_title}</span> <span className="text-muted">· {deal.status === "disputed" ? "Under review" : "Handoff confirmed by one side"}</span></span>
                <Link href="/deals" className="shrink-0 font-semibold underline">Open deals</Link>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <section aria-labelledby="confirm-heading" className="mt-6 space-y-4 rounded-xl border border-line p-4 text-sm">
          <h2 id="confirm-heading" className="font-bold">Confirm</h2>
          <label className="block font-semibold">
            Why are you leaving? <span className="font-normal text-muted">(optional)</span>
            <select value={reason} onChange={(event) => setReason(event.target.value)} className="field mt-1.5 h-11 w-full px-3 font-normal">
              <option value="">Prefer not to say</option>
              {REASONS.map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <label className="block font-semibold">
            Your password
            <input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} className="field mt-1.5 h-11 w-full px-3 font-normal" />
          </label>
          <label className="flex items-start gap-2">
            <input type="checkbox" checked={understood} onChange={(event) => setUnderstood(event.target.checked)} className="mt-0.5 accent-[var(--brand)]" />
            I understand my open requests will be withdrawn and my listings hidden.
          </label>
          {error && <p role="alert" className="text-[var(--danger)]">{error}</p>}
          <button type="button" onClick={submit} disabled={working || !password || !understood} className="btn w-full bg-[var(--danger)] text-white disabled:opacity-50">
            {working ? "Deactivating…" : "Deactivate account"}
          </button>
        </section>
      )}
    </main>
  );
}
