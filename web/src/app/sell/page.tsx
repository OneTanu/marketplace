import type { Metadata } from "next";

import { Placeholder } from "@/components/placeholder";

export const metadata: Metadata = { title: "Sell" };

export default function SellPage() {
  return <Placeholder title="Sell an item" note="Create a listing with photos (workstream 2: Listings)." />;
}
