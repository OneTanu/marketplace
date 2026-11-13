import { api, errorMessage } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type ProfileUpdateErrors = {
  instagram_handle?: string;
  profile_description?: string;
  detail?: string;
};

function failed(response: Response): never {
  throw new Error(`Request failed with ${response.status}`);
}

export async function getSchools() {
  const { data, response } = await api.GET("/api/schools/");
  return data ?? failed(response);
}

export async function getSchool(slug: string) {
  const { data, response } = await api.GET("/api/schools/{slug}/", { params: { path: { slug } } });
  return data ?? failed(response);
}

export async function getCurrentUser() {
  const { data, response } = await api.GET("/api/me/", { cache: "no-store" });
  if (response.status === 401 || response.status === 403) return null;
  return data ?? failed(response);
}

export async function searchUsers(query: string, school?: string) {
  const { data, response } = await api.GET("/api/users/", {
    params: { query: { q: query, ...(school ? { school } : {}) } },
  });
  return data ?? failed(response);
}

export async function getPublicUser(username: string) {
  const { data, response } = await api.GET("/api/users/{username}/", {
    params: { path: { username } },
  });
  return data ?? failed(response);
}

export async function getPublicUserListings(username: string) {
  const { data, response } = await api.GET("/api/users/{username}/listings/", {
    params: { path: { username } },
  });
  return data ?? failed(response);
}

export async function updateCurrentUser(update: {
  instagram_handle: string;
  profile_description: string;
}) {
  try {
    const { data, error } = await api.PATCH("/api/me/", { body: update });
    if (data) return { user: data, errors: {} as ProfileUpdateErrors };
    const instagramError = errorMessage(error, "instagram_handle");
    const descriptionError = errorMessage(error, "profile_description");
    const errors: ProfileUpdateErrors = {
      instagram_handle: instagramError,
      profile_description: descriptionError,
      detail:
        errorMessage(error, "detail") ??
        (instagramError || descriptionError
          ? undefined
          : "We couldn’t save your profile. Please try again."),
    };
    return { errors };
  } catch {
    return { errors: { detail: "Tanu couldn’t reach the server. Check your connection and try again." } };
  }
}

export async function setFollowing(username: string, following: boolean) {
  const params = { params: { path: { username } } };
  if (!following) {
    const { error, response } = await api.DELETE("/api/users/{username}/follow/", params);
    if (!response.ok) throw new Error(errorMessage(error, "detail") ?? "We couldn’t update this follow.");
    return null;
  }
  const { data, error } = await api.POST("/api/users/{username}/follow/", params);
  if (!data) throw new Error(errorMessage(error, "detail") ?? "We couldn’t update this follow.");
  return data;
}

export async function homeMarketplacePath() {
  try {
    const user = await getCurrentUser();
    return user?.school ? `/schools/${user.school.slug}` : "/";
  } catch {
    return "/";
  }
}

export type FollowDirection = "followers" | "following";

/** One page of a student's followers or follows. Null when signed out. */
export async function getFollowList(username: string, direction: FollowDirection, cursor?: string) {
  const options = { params: { path: { username }, query: cursor ? { cursor } : {} } };
  const { data, response } = direction === "followers"
    ? await api.GET("/api/users/{username}/followers/", options)
    : await api.GET("/api/users/{username}/following/", options);
  if (response.status === 401 || response.status === 403) return null;
  return data ?? failed(response);
}

type ProfilePhotoUploadRequest = components["schemas"]["ProfilePhotoUploadRequest"];

/** Upload a new profile photo. Returns the updated account, or throws with a message to show. */
export async function uploadProfilePhoto(file: File) {
  const body = new FormData();
  body.append("photo", file);
  try {
    const { data, error } = await api.POST("/api/me/photo/", {
      // Sent as this multipart FormData; the generated type describes the file as a string.
      body: {} as ProfilePhotoUploadRequest,
      bodySerializer: () => body,
    });
    if (data) return data;
    throw new Error(errorMessage(error, "photo") ?? errorMessage(error, "detail") ?? "We couldn’t upload this photo. Try another one.");
  } catch (caught) {
    if (caught instanceof Error && caught.message !== "Failed to fetch") throw caught;
    throw new Error("Tanu couldn’t reach the server. Check your connection and try again.");
  }
}

export async function removeProfilePhoto() {
  const { data, error } = await api.DELETE("/api/me/photo/");
  if (!data) throw new Error(errorMessage(error, "detail") ?? "We couldn’t remove your photo. Try again.");
  return data;
}
