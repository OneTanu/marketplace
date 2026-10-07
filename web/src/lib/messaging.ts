export type MessagingUser = {
  id: number;
  username: string;
  first_name: string;
  school: { name: string; short_name: string; slug: string } | null;
};

export type ChatMessage = {
  id: number;
  conversation: number;
  sender: MessagingUser;
  body: string;
  created_at: string;
  is_mine: boolean;
};

export type MessagePage = {
  messages: ChatMessage[];
  has_more: boolean;
};

export type Conversation = {
  id: number;
  other_user: MessagingUser;
  latest_message: ChatMessage | null;
  unread_count: number;
  created_at: string;
  last_message_at: string | null;
};

function cookie(name: string) {
  return document.cookie.split("; ").find((part) => part.startsWith(`${name}=`))?.split("=").slice(1).join("=");
}

async function csrfToken() {
  let token = cookie("csrftoken");
  if (!token) {
    await fetch("/api/auth/browser/v1/config", { credentials: "same-origin" });
    token = cookie("csrftoken");
  }
  return token;
}

async function api<T>(path: string, init: RequestInit = {}) {
  const method = init.method?.toUpperCase() ?? "GET";
  const headers = new Headers(init.headers);
  if (method !== "GET" && method !== "HEAD") {
    const csrf = await csrfToken();
    if (csrf) headers.set("X-CSRFToken", decodeURIComponent(csrf));
  }
  if (init.body) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...init, headers, credentials: "same-origin" });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : `Request failed with ${response.status}`;
    throw new Error(detail);
  }
  return body as T;
}

export function listConversations() {
  return api<Conversation[]>("/api/conversations/");
}

export function getConversation(id: number) {
  return api<Conversation>(`/api/conversations/${id}/`);
}

export function startConversation(username: string) {
  return api<Conversation>("/api/conversations/", {
    method: "POST",
    body: JSON.stringify({ username }),
  });
}

export function listMessages(id: number, cursor: { beforeId?: number; afterId?: number } = {}) {
  const params = new URLSearchParams();
  if (cursor.beforeId) params.set("before_id", String(cursor.beforeId));
  if (cursor.afterId) params.set("after_id", String(cursor.afterId));
  const query = params.toString();
  return api<MessagePage>(`/api/conversations/${id}/messages/${query ? `?${query}` : ""}`);
}

export function sendMessage(id: number, body: string) {
  return api<ChatMessage>(`/api/conversations/${id}/messages/`, {
    method: "POST",
    body: JSON.stringify({ body }),
  });
}

export async function markConversationRead(id: number, messageId?: number) {
  await api<Record<string, never>>(`/api/conversations/${id}/read/`, {
    method: "POST",
    body: JSON.stringify(messageId ? { message_id: messageId } : {}),
  });
}

export function getUnreadCount() {
  return api<{ unread_count: number }>("/api/conversations/unread-count/");
}
