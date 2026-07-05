import type { Metadata } from "next";

import { Placeholder } from "@/components/placeholder";

export const metadata: Metadata = { title: "Inbox" };

export default function InboxPage() {
  return <Placeholder title="Inbox" note="Conversations and offers (workstreams 4 and 5)." />;
}
