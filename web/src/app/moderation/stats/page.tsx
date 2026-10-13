import type { Metadata } from "next";

import { ModerationStatsView } from "@/components/moderation/stats";

export const metadata: Metadata = { title: "Moderation stats", robots: { index: false } };

export default function ModerationStatsPage() {
  return <ModerationStatsView />;
}
