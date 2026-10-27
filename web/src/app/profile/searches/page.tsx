import type { Metadata } from "next";

import { SavedSearches } from "@/components/profile/saved-searches";

export const metadata: Metadata = { title: "Saved searches" };

export default function SavedSearchesPage() {
  return <SavedSearches />;
}
