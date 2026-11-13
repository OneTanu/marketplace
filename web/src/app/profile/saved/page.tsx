import type { Metadata } from "next";
import Link from "next/link";

import { SavedListings } from "@/components/profile/saved-listings";

export const metadata: Metadata = { title: "Saved" };

export default function SavedPage() {
  return <div className="mx-auto min-h-[70vh] w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
    <Link href="/profile" className="inline-flex min-h-11 items-center text-sm font-bold text-muted hover:text-ink">← Back to profile</Link>
    <h1 className="type-wide mt-2 mb-6 text-3xl font-black">Saved</h1>
    <SavedListings />
  </div>;
}
