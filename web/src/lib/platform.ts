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
  first_name: string;
  last_name: string;
  school: SchoolMarketplace | null;
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
  const response = await fetch("/api/me/", { credentials: "same-origin" });
  if (response.status === 401 || response.status === 403) return null;
  if (!response.ok) throw new Error(`Request failed with ${response.status}`);
  return response.json() as Promise<CurrentUser>;
}

export async function homeMarketplacePath() {
  try {
    const user = await getCurrentUser();
    return user?.school ? `/schools/${user.school.slug}` : "/";
  } catch {
    return "/";
  }
}
