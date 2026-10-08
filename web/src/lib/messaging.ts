import { api, errorMessage } from "@/lib/api/client";

// Throws the API's `detail` (e.g. "You cannot message yourself.") when a request fails.
function failed(error: unknown, response: Response): never {
  throw new Error(errorMessage(error, "detail") ?? `Request failed with ${response.status}`);
}

export async function listConversations() {
  const { data, error, response } = await api.GET("/api/conversations/");
  return data ?? failed(error, response);
}

export async function getConversation(id: number) {
  const { data, error, response } = await api.GET("/api/conversations/{id}/", {
    params: { path: { id } },
  });
  return data ?? failed(error, response);
}

export async function startConversation(username: string) {
  const { data, error, response } = await api.POST("/api/conversations/", { body: { username } });
  return data ?? failed(error, response);
}

export async function listMessages(id: number, cursor: { beforeId?: number; afterId?: number } = {}) {
  const query: { before_id?: number; after_id?: number } = {};
  if (cursor.beforeId) query.before_id = cursor.beforeId;
  if (cursor.afterId) query.after_id = cursor.afterId;
  const { data, error, response } = await api.GET("/api/conversations/{id}/messages/", {
    params: { path: { id }, query },
  });
  return data ?? failed(error, response);
}

export async function sendMessage(id: number, body: string) {
  const { data, error, response } = await api.POST("/api/conversations/{id}/messages/", {
    params: { path: { id } },
    body: { body },
  });
  return data ?? failed(error, response);
}

export async function markConversationRead(id: number, messageId?: number) {
  const { error, response } = await api.POST("/api/conversations/{id}/read/", {
    params: { path: { id } },
    body: messageId ? { message_id: messageId } : {},
  });
  if (!response.ok) failed(error, response);
}

export async function getUnreadCount() {
  const { data, error, response } = await api.GET("/api/conversations/unread-count/");
  return data ?? failed(error, response);
}
