import type { Metadata } from "next";
import { Suspense } from "react";

import { SearchResults } from "@/components/discovery/search-results";

export const metadata: Metadata = { title: "Search" };

export default function SearchPage() {
  return <Suspense fallback={<main className="mx-auto min-h-[70vh] max-w-6xl animate-pulse px-4 py-10 sm:px-6"><div className="h-40 rounded-3xl bg-foreground/5" /></main>}><SearchResults /></Suspense>;
}
