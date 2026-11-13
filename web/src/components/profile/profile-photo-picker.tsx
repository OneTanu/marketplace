"use client";

import { useRef, useState, type ChangeEvent } from "react";

import type { components } from "@/lib/api/schema";
import { MAX_PHOTO_BYTES, PHOTO_TYPES } from "@/lib/listing-options";
import { removeProfilePhoto, uploadProfilePhoto } from "@/lib/platform";

type CurrentUser = components["schemas"]["CurrentUser"];

/** "Add photo" / "Change photo" on your own ID card. Shows its own errors via onError. */
export function ProfilePhotoButton({ hasPhoto, onChange, onError }: { hasPhoto: boolean; onChange: (user: CurrentUser) => void; onError: (message: string) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  async function choose(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = ""; // so choosing the same file again still fires
    if (!file) return;
    onError("");
    if (!PHOTO_TYPES.includes(file.type)) return onError("Choose a JPEG, PNG or WebP photo.");
    if (file.size > MAX_PHOTO_BYTES) return onError("That photo is larger than 10 MB. Try a smaller one.");
    setBusy(true);
    try {
      onChange(await uploadProfilePhoto(file));
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "We couldn’t upload this photo. Try another one.");
    } finally {
      setBusy(false);
    }
  }

  return <>
    <input ref={input} type="file" accept={PHOTO_TYPES.join(",")} onChange={choose} className="sr-only" tabIndex={-1} aria-hidden="true" />
    <button type="button" onClick={() => input.current?.click()} disabled={busy} className="w-full rounded-md bg-ink/80 px-2 py-1.5 text-xs font-bold text-white backdrop-blur transition hover:bg-ink disabled:opacity-70">
      {busy ? "Uploading…" : hasPhoto ? "Change photo" : "Add photo"}
    </button>
  </>;
}

export function RemoveProfilePhotoButton({ onChange, onError }: { onChange: (user: CurrentUser) => void; onError: (message: string) => void }) {
  const [busy, setBusy] = useState(false);

  async function remove() {
    if (!window.confirm("Remove your profile photo?")) return;
    setBusy(true);
    onError("");
    try {
      onChange(await removeProfilePhoto());
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "We couldn’t remove your photo. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return <button type="button" onClick={remove} disabled={busy} className="text-sm font-semibold text-muted hover:text-ink hover:underline">{busy ? "Removing…" : "Remove photo"}</button>;
}
