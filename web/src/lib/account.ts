import { api, requestFailed } from "@/lib/api/client";

/** What deactivating would do right now: deals to settle first, deals withdrawn, listings hidden. */
export async function getDeactivationPreview() {
  const { data, error, response } = await api.GET("/api/me/deactivation/");
  return data ?? requestFailed(error, response);
}

export async function deactivateAccount(password: string, reason: string) {
  const { error, response } = await api.POST("/api/me/deactivate/", { body: { password, reason } });
  if (!response.ok) requestFailed(error, response);
}

/** Turn a deactivated account back on (signed out), then log in as usual. */
export async function reactivateAccount(email: string, password: string) {
  const { error, response } = await api.POST("/api/account/reactivate/", { body: { email, password } });
  if (!response.ok) requestFailed(error, response);
}
