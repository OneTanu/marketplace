"use client";

import { useRef, useState, type ChangeEvent } from "react";

import type { components } from "@/lib/api/schema";
import { MAX_PHOTO_BYTES, PHOTO_TYPES } from "@/lib/listing-options";
import { removeProfilePhoto, uploadProfilePhoto } from "@/lib/platform";

import { Avatar } from "./avatar";

type CurrentUser = components["schemas"]["CurrentUser"];

/** The profile photo row at the top of Edit profile: the current photo (or initial), then Add or
 * Change, and Remove. Reports the updated account through onChange. */
export function ProfilePhotoField({ user, onChange }: { user: CurrentUser; onChange: (user: CurrentUser) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<"upload" | "remove">();
  const [error, setError] = useState("");
  const hasPhoto = Boolean(user.profile_photo_url);

  async function choose(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = ""; // so choosing the same file again still fires
    if (!file) return;
    setError("");
    if (!PHOTO_TYPES.includes(file.type)) return setError("Choose a JPEG, PNG or WebP photo.");
    if (file.size > MAX_PHOTO_BYTES) return setError("That photo is larger than 10 MB. Try a smaller one.");
    setBusy("upload");
    try {
      onChange(await uploadProfilePhoto(file));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We couldn’t upload this photo. Try another one.");
    } finally {
      setBusy(undefined);
    }
  }

  async function remove() {
    if (!window.confirm("Remove your profile photo?")) return;
    setBusy("remove");
    setError("");
    try {
      onChange(await removeProfilePhoto());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We couldn’t remove your photo. Try again.");
    } finally {
      setBusy(undefined);
    }
  }

  return (
    <div>
      <div className="flex items-center gap-4">
        <Avatar photoUrl={user.profile_photo_url} firstName={user.first_name} username={user.username} className="size-18 rounded-full text-2xl" />
        <div className="flex flex-wrap gap-2">
          <input ref={input} type="file" accept={PHOTO_TYPES.join(",")} onChange={choose} className="sr-only" tabIndex={-1} aria-hidden="true" />
          <button type="button" onClick={() => input.current?.click()} disabled={Boolean(busy)} className="btn btn-secondary btn-sm">
            {busy === "upload" ? "Uploading…" : hasPhoto ? "Change photo" : "Add photo"}
          </button>
          {hasPhoto && <button type="button" onClick={remove} disabled={Boolean(busy)} className="btn btn-quiet btn-sm">{busy === "remove" ? "Removing…" : "Remove"}</button>}
        </div>
      </div>
      {error && <p role="alert" className="mt-2 text-sm text-[var(--danger)]">{error}</p>}
    </div>
  );
}
