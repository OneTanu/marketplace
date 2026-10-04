import type { Metadata } from "next";

import { SearchLanding } from "@/components/discovery/search-landing";

export const metadata: Metadata = { title: "Search" };

export default function SearchPage() {
  return <SearchLanding />;
}
