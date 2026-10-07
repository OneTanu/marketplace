"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import {
  getCurrentUser,
  updateCurrentUser,
  type CurrentUser,
  type ProfileUpdateErrors,
} from "@/lib/platform";

type ProfileTab = "selling" | "sold" | "bookmarks";

function initials(user: CurrentUser) {
  return (user.first_name[0] || user.username[0] || "T").toUpperCase();
}

function InstagramLink({ handle }: { handle: string }) {
  return (
    <a
      className="inline-flex items-center gap-2 font-semibold text-ink underline decoration-ink/25 underline-offset-4 transition hover:decoration-ink"
      href={`https://www.instagram.com/${encodeURIComponent(handle)}/`}
      target="_blank"
      rel="noreferrer"
    >
      @{handle} <span aria-hidden="true">↗</span>
    </a>
  );
}

function EmptyCollection({ tab }: { tab: ProfileTab }) {
  const content = {
    selling: {
      title: "Nothing for sale yet",
      note: "When you publish a listing, it will appear here for other students to find.",
      action: <Link href="/sell" className="btn btn-primary">Create a listing</Link>,
    },
    sold: {
      title: "No sold items yet",
      note: "Completed sales will appear here once the deals system is connected.",
      action: null,
    },
    bookmarks: {
      title: "No bookmarks yet",
      note: "Save interesting listings while browsing and they will be collected here.",
      action: <Link href="/search" className="btn btn-secondary">Browse listings</Link>,
    },
  }[tab];

  return (
    <div className="grid min-h-64 place-items-center rounded-3xl border border-dashed border-line bg-white/45 px-6 text-center">
      <div className="max-w-sm py-10">
        <div className="mx-auto mb-4 grid size-12 place-items-center rounded-2xl bg-[var(--ink-soft)] text-xl text-ink" aria-hidden="true">◇</div>
        <h2 className="text-lg font-bold">{content.title}</h2>
        <p className="mt-2 text-sm leading-6 text-muted">{content.note}</p>
        {content.action && <div className="mt-5">{content.action}</div>}
      </div>
    </div>
  );
}

export function ProfileClient() {
  const [user, setUser] = useState<CurrentUser | null>();
  const [loadError, setLoadError] = useState(false);
  const [editing, setEditing] = useState(false);
  const [pending, setPending] = useState(false);
  const [saved, setSaved] = useState(false);
  const [errors, setErrors] = useState<ProfileUpdateErrors>({});
  const [tab, setTab] = useState<ProfileTab>("selling");

  useEffect(() => {
    let active = true;
    getCurrentUser()
      .then((currentUser) => active && setUser(currentUser))
      .catch(() => active && setLoadError(true));
    return () => { active = false; };
  }, []);

  async function retryProfile() {
    setLoadError(false);
    setUser(undefined);
    try {
      setUser(await getCurrentUser());
    } catch {
      setLoadError(true);
    }
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setSaved(false);
    setErrors({});
    const data = new FormData(event.currentTarget);
    const result = await updateCurrentUser({
      profile_description: String(data.get("profile_description") ?? ""),
      instagram_handle: String(data.get("instagram_handle") ?? ""),
    });
    if (result.user) {
      setUser(result.user);
      setEditing(false);
      setSaved(true);
    } else {
      setErrors(result.errors);
    }
    setPending(false);
  }

  if (user === undefined) {
    if (loadError) {
      return <main className="mx-auto grid min-h-[70vh] max-w-xl place-items-center px-4 py-12 text-center"><div className="rounded-2xl bg-surface p-8"><h1 className="type-wide text-2xl font-black">We couldn’t load your profile</h1><p className="mt-3 leading-7 text-muted">Your session may still be active. Check the connection and try loading your account again.</p><button type="button" onClick={retryProfile} className="btn btn-primary mt-6">Try again</button></div></main>;
    }
    return <main className="mx-auto min-h-[70vh] max-w-6xl animate-pulse px-4 py-10 sm:px-6"><div className="h-72 rounded-3xl border border-line bg-white/60" /></main>;
  }

  if (user === null) {
    return (
      <main className="mx-auto grid min-h-[70vh] max-w-xl place-items-center px-4 py-12 text-center">
        <div className="rounded-3xl border border-line bg-surface p-8 shadow-sm">
          <div className="mx-auto grid size-16 place-items-center rounded-2xl bg-[var(--ink-soft)] text-2xl font-black text-ink">T</div>
          <h1 className="mt-5 text-2xl font-bold tracking-tight">Sign in to view your profile</h1>
          <p className="mt-3 leading-7 text-muted">Your profile, school identity, and marketplace activity are connected to your verified student account.</p>
          <Link href="/account/login" className="mt-6 inline-flex btn btn-primary">Log in</Link>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 pb-28 sm:px-6 sm:py-12 desktop:pb-12">
      <section className="animate-in overflow-hidden rounded-[2rem] border border-line bg-surface shadow-[0_18px_60px_rgb(20_35_29/8%)]">
        <div className="h-28 bg-ink sm:h-36" />
        <div className="px-5 pb-7 sm:px-8">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
            <div className="-mt-12 flex flex-col items-start gap-4 sm:-mt-14 sm:flex-row sm:items-end">
              <div className="grid size-24 shrink-0 place-items-center rounded-[1.75rem] border-4 border-surface bg-[var(--brand-soft)] text-4xl font-black text-brand shadow-sm sm:size-28">{initials(user)}</div>
              <div className="pb-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="type-wide text-3xl font-black">{user.first_name || `@${user.username}`}</h1>
                  <span className="rounded bg-[var(--brand-soft)] px-2 py-0.5 text-xs font-bold text-brand">Verified student</span>
                </div>
                <p className="mt-1 font-medium text-muted">@{user.username}</p>
              </div>
            </div>
            <button onClick={() => { setEditing((value) => !value); setSaved(false); setErrors({}); }} className="btn btn-secondary">{editing ? "Cancel" : "Edit profile"}</button>
          </div>

          {editing ? (
            <form onSubmit={saveProfile} className="mt-7 max-w-2xl space-y-5 rounded-2xl border border-line bg-white/65 p-5">
              <label className="block">
                <span className="flex justify-between text-sm font-bold">Description <span className="font-normal text-muted">Optional · 300 characters</span></span>
                <textarea name="profile_description" defaultValue={user.profile_description} maxLength={300} rows={4} className="mt-2 w-full resize-none rounded-xl border border-line bg-white px-4 py-3 text-[15px] outline-none transition focus:border-brand focus:ring-4 focus:ring-[var(--brand-soft)]" placeholder="Tell other students a little about you and what you sell." />
                {errors.profile_description && <span className="mt-1.5 block text-sm text-[var(--danger)]">{errors.profile_description}</span>}
              </label>
              <label className="block">
                <span className="flex justify-between text-sm font-bold">Instagram <span className="font-normal text-muted">Optional and public</span></span>
                <div className="mt-2 flex h-12 items-center rounded-xl border border-line bg-white px-4 focus-within:border-brand focus-within:ring-4 focus-within:ring-[var(--brand-soft)]">
                  <span className="text-muted">@</span>
                  <input name="instagram_handle" defaultValue={user.instagram_handle ?? ""} maxLength={100} className="h-full min-w-0 flex-1 bg-transparent pl-1 outline-none" placeholder="yourhandle" />
                </div>
                <p className="mt-1.5 text-xs leading-5 text-muted">Each Instagram handle can be connected to only one Tanu account. Instagram ownership is not yet verified by Tanu.</p>
                {errors.instagram_handle && <span className="mt-1.5 block text-sm text-[var(--danger)]">{errors.instagram_handle}</span>}
              </label>
              {errors.detail && <p role="alert" className="text-sm text-[var(--danger)]">{errors.detail}</p>}
              <div className="flex justify-end"><button disabled={pending} className="btn btn-primary">{pending ? "Saving…" : "Save profile"}</button></div>
            </form>
          ) : (
            <div className="mt-6 grid gap-5 lg:grid-cols-[1fr_auto] lg:items-end">
              <div>
                <p className="max-w-2xl leading-7 text-foreground/80">{user.profile_description || "Add a short description so other students know a little about you and what you usually sell."}</p>
                <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted">
                  {user.school && <span className="font-semibold text-foreground">{user.school.name}</span>}
                  {user.instagram_handle && <InstagramLink handle={user.instagram_handle} />}
                </div>
                {saved && <p className="mt-3 text-sm font-semibold text-ink">Profile saved.</p>}
              </div>
              <div className="flex gap-6 text-sm">
                <div><strong className="block text-lg text-foreground">{user.follower_count}</strong><span className="text-muted">Followers</span></div>
                <div><strong className="block text-lg text-foreground">{user.following_count}</strong><span className="text-muted">Following</span></div>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="mt-8 animate-in [animation-delay:100ms]">
        <div className="mb-5 flex gap-1 overflow-x-auto border-b border-line" role="tablist" aria-label="Profile activity">
          {([["selling", "Selling"], ["sold", "Sold"], ["bookmarks", "Bookmarks"]] as const).map(([value, label]) => (
            <button key={value} role="tab" aria-selected={tab === value} onClick={() => setTab(value)} className="relative min-w-max px-5 py-3 text-sm font-bold text-muted transition hover:text-foreground aria-[selected=true]:text-foreground after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:rounded-full after:bg-brand after:opacity-0 aria-[selected=true]:after:opacity-100">{label}</button>
          ))}
        </div>
        <EmptyCollection tab={tab} />
      </section>
    </main>
  );
}
