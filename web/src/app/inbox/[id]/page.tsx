import type { Metadata } from "next";

import { ChatClient } from "@/components/messaging/chat-client";

export const metadata: Metadata = { title: "Conversation" };

export default async function ConversationPage({ params, searchParams }: PageProps<"/inbox/[id]">) {
  const { id } = await params;
  const { listing } = await searchParams;
  const listingId = typeof listing === "string" ? Number(listing) : undefined;
  return <ChatClient conversationId={Number(id)} listingId={listingId} />;
}
