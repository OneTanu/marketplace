export type SchoolMarketplace = {
  name: string;
  short_name: string;
  slug: string;
  signup_is_open: boolean;
  marketplace_status: "planned" | "waitlist" | "open" | "paused";
  city: string;
  state: string;
  country_code: string;
  timezone: string;
  domains: string[];
};

export type CurrentUser = {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  school: SchoolMarketplace | null;
  instagram_handle: string | null;
  profile_description: string;
  follower_count: number;
  following_count: number;
};

export type ProfileUpdateErrors = {
  instagram_handle?: string;
  profile_description?: string;
  detail?: string;
};

export type PublicUser = {
  id: number;
  username: string;
  first_name: string;
  school: SchoolMarketplace | null;
  instagram_handle: string;
  profile_description: string;
  follower_count: number;
  following_count: number;
  is_following: boolean;
  is_self: boolean;
};

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { credentials: "same-origin" });
  if (!response.ok) throw new Error(`Request failed with ${response.status}`);
  return response.json() as Promise<T>;
}

export function getSchools() {
  return getJson<SchoolMarketplace[]>("/api/schools/");
}

export function getSchool(slug: string) {
  return getJson<SchoolMarketplace>(`/api/schools/${encodeURIComponent(slug)}/`);
}

export async function getCurrentUser() {
  const response = await fetch("/api/me/", { credentials: "same-origin", cache: "no-store" });
  if (response.status === 401 || response.status === 403) return null;
  if (!response.ok) throw new Error(`Request failed with ${response.status}`);
  return response.json() as Promise<CurrentUser>;
}

export function searchUsers(query: string, school?: string) {
  const params = new URLSearchParams({ q: query });
  if (school) params.set("school", school);
  return getJson<PublicUser[]>(`/api/users/?${params.toString()}`);
}

export function getPublicUser(username: string) {
  return getJson<PublicUser>(`/api/users/${encodeURIComponent(username)}/`);
}

function cookie(name: string) {
  return document.cookie
    .split("; ")
    .find((part) => part.startsWith(`${name}=`))
    ?.split("=")
    .slice(1)
    .join("=");
}

export async function updateCurrentUser(update: {
  instagram_handle: string;
  profile_description: string;
}): Promise<{ user?: CurrentUser; errors: ProfileUpdateErrors }> {
  let csrf = cookie("csrftoken");
  if (!csrf) {
    await fetch("/api/auth/browser/v1/config", { credentials: "same-origin" });
    csrf = cookie("csrftoken");
  }
  try {
    const response = await fetch("/api/me/", {
      method: "PATCH",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        ...(csrf ? { "X-CSRFToken": decodeURIComponent(csrf) } : {}),
      },
      body: JSON.stringify(update),
    });
    const body = (await response.json().catch(() => ({}))) as Record<string, unknown>;
    if (response.ok) return { user: body as CurrentUser, errors: {} };
    const message = (key: string) => {
      const value = body[key];
      if (Array.isArray(value)) return String(value[0]);
      return typeof value === "string" ? value : undefined;
    };
    const instagramError = message("instagram_handle");
    const descriptionError = message("profile_description");
    return {
      errors: {
        instagram_handle: instagramError,
        profile_description: descriptionError,
        detail:
          message("detail") ??
          (instagramError || descriptionError
            ? undefined
            : "We couldn’t save your profile. Please try again."),
      },
    };
  } catch {
    return { errors: { detail: "Tanu couldn’t reach the server. Check your connection and try again." } };
  }
}

export async function setFollowing(username: string, following: boolean) {
  let csrf = cookie("csrftoken");
  if (!csrf) {
    await fetch("/api/auth/browser/v1/config", { credentials: "same-origin" });
    csrf = cookie("csrftoken");
  }
  const response = await fetch(`/api/users/${encodeURIComponent(username)}/follow/`, {
    method: following ? "POST" : "DELETE",
    credentials: "same-origin",
    headers: csrf ? { "X-CSRFToken": decodeURIComponent(csrf) } : {},
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(body.detail ?? "We couldn’t update this follow.");
  }
  if (response.status === 204) return null;
  return response.json() as Promise<PublicUser>;
}

export async function homeMarketplacePath() {
  try {
    const user = await getCurrentUser();
    return user?.school ? `/schools/${user.school.slug}` : "/";
  } catch {
    return "/";
  }
}
