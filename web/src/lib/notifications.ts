import { api, requestFailed } from "@/lib/api/client";

export async function listNotifications() {
  const { data, error, response } = await api.GET("/api/notifications/");
  return data ?? requestFailed(error, response);
}

export async function getUnreadNotificationCount() {
  const { data, error, response } = await api.GET("/api/notifications/unread-count/");
  return data ?? requestFailed(error, response);
}

/** Mark some notifications read, or all of them with no ids. Returns the new unread count. */
export async function markNotificationsRead(ids?: number[]) {
  const { data, error, response } = await api.POST("/api/notifications/read/", {
    body: ids ? { ids } : {},
  });
  return data ?? requestFailed(error, response);
}
