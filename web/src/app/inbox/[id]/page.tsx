import type { Metadata } from "next";

import { ChatClient } from "@/components/messaging/chat-client";

export const metadata: Metadata = { title: "Conversation" };

export default async function ConversationPage({ params }: PageProps<"/inbox/[id]">) {
  const { id } = await params;
  return <ChatClient conversationId={Number(id)} />;
}
