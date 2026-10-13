import type { Metadata } from "next";

import { ModerationQueue } from "@/components/moderation/queue";

export const metadata: Metadata = { title: "Moderation", robots: { index: false } };

export default function ModerationPage() {
  return <ModerationQueue />;
}
