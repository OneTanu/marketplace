import type { Metadata } from "next";
import Link from "next/link";

import { MyListings } from "./my-listings";

export const metadata: Metadata = { title: "My listings" };

export default function MyListingsPage() {
  return (
    <section className="mx-auto w-full max-w-6xl px-4 py-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">My listings</h1>
        <Link
          href="/sell"
          className="rounded-full bg-foreground px-4 py-2 text-sm font-semibold text-background"
        >
          Sell an item
        </Link>
      </div>
      <MyListings />
    </section>
  );
}
