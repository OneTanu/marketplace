import type { Metadata } from "next";

import { Placeholder } from "@/components/placeholder";

export const metadata: Metadata = { title: "Search" };

export default function SearchPage() {
  return <Placeholder title="Search" note="Search and filters for listings (workstream 3: Discovery)." />;
}
