"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { FocusedHeader } from "@/components/ui/focused-header";
import { getCurrentUser, updateCurrentUser, type ProfileUpdateErrors } from "@/lib/platform";
import type { components } from "@/lib/api/schema";

type CurrentUser = components["schemas"]["CurrentUser"];

/** Edit profile (/profile/edit), a focused screen: the description and Instagram handle that
 * other students see on your public profile. */
export function EditProfile() {
  // undefined while loading, null when signed out.
  const [user, setUser] = useState<CurrentUser | null>();
  const [loadError, setLoadError] = useState(false);
  const [pending, setPending] = useState(false);
  const [saved, setSaved] = useState(false);
  const [errors, setErrors] = useState<ProfileUpdateErrors>({});

  useEffect(() => {
    let active = true;
    getCurrentUser()
      .then((current) => active && setUser(current))
      .catch(() => active && setLoadError(true));
    return () => { active = false; };
  }, []);

  async function save(event: FormEvent<HTMLFormElement>) {
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
      setSaved(true);
    } else {
      setErrors(result.errors);
    }
    setPending(false);
  }

  const header = <FocusedHeader title="Edit profile" backHref="/profile" backLabel="Back to profile" />;
  const shell = "mx-auto w-full max-w-2xl px-4 py-6 sm:px-6";

  if (user === undefined) {
    return <>{header}<div className={shell}>
      {loadError
        ? <div role="alert" className="rounded-2xl bg-surface p-6 text-center"><p className="font-bold">Couldn’t load your profile</p><p className="mt-1 text-sm text-muted">Check your connection and refresh the page.</p></div>
        : <div aria-busy="true" aria-label="Loading your profile" className="h-72 animate-pulse rounded-2xl bg-surface" />}
    </div></>;
  }
  if (user === null) {
    return <>{header}<div className={`${shell} text-center`}><p className="font-bold">Log in to edit your profile</p><Link href="/account/login" className="btn btn-primary mt-4">Log in</Link></div></>;
  }

  return <>
    {header}
    <form onSubmit={save} className={`${shell} space-y-6`}>
      <p className="text-muted">Other students see this on your profile.</p>
      <label className="block">
        <span className="flex justify-between gap-3 text-sm font-bold">Description <span className="font-normal text-muted">Optional · 300 characters</span></span>
        <textarea name="profile_description" defaultValue={user.profile_description} maxLength={300} rows={4} className="field mt-2 h-auto resize-none py-3 leading-6" placeholder="Tell other students a little about you and what you sell." />
        {errors.profile_description && <span className="mt-1.5 block text-sm text-[var(--danger)]">{errors.profile_description}</span>}
      </label>
      <label className="block">
        <span className="flex justify-between gap-3 text-sm font-bold">Instagram <span className="font-normal text-muted">Optional and public</span></span>
        <span className="field mt-2 flex items-center">
          <span className="text-muted">@</span>
          <input name="instagram_handle" defaultValue={user.instagram_handle} maxLength={100} autoComplete="off" autoCapitalize="none" spellCheck={false} className="h-full min-w-0 flex-1 bg-transparent pl-1 outline-none" placeholder="yourhandle" />
        </span>
        <span className="mt-1.5 block text-fine text-muted">Each Instagram handle can be connected to only one Tanu account. Tanu doesn’t verify that you own it yet.</span>
        {errors.instagram_handle && <span className="mt-1.5 block text-sm text-[var(--danger)]">{errors.instagram_handle}</span>}
      </label>
      {errors.detail && <p role="alert" className="text-sm text-[var(--danger)]">{errors.detail}</p>}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
        {saved && <p role="status" className="text-sm font-semibold text-ink">Profile saved. <Link href={`/users/${encodeURIComponent(user.username)}`} className="underline decoration-kraft decoration-2 underline-offset-4">View profile</Link></p>}
        <button disabled={pending} className="btn btn-primary w-full sm:w-auto">{pending ? "Saving…" : "Save profile"}</button>
      </div>
    </form>
  </>;
}
