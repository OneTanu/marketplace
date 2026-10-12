import { expect, type BrowserContext, type Locator } from "@playwright/test";

type MeetingSpot = { id: number; name: string };

/**
 * Gives whoever is signed in to `context` every UMD meetup spot and all-day availability, so
 * buyers always have times to pick and the Sell form is unlocked. Returns the spots.
 */
export async function setMeetupPreferences(context: BrowserContext, baseURL: string) {
  const api = context.request;
  const spots = await api.get("/api/schools/umd/meeting-spots/");
  expect(spots.ok()).toBe(true);
  const meetingSpots = (await spots.json()) as MeetingSpot[];
  expect(meetingSpots.length, "UMD meetup spots from the schools migration").toBeGreaterThan(0);

  const csrfToken = (await context.cookies()).find((c) => c.name === "csrftoken")?.value;
  const response = await api.put("/api/meetup-preferences/", {
    data: {
      meeting_spot_ids: meetingSpots.map((spot) => spot.id),
      windows: [0, 1, 2, 3, 4, 5, 6].map((weekday) => ({
        weekday,
        start_time: "00:00",
        end_time: "23:59",
      })),
      overrides: [],
    },
    headers: { "X-CSRFToken": csrfToken!, Origin: baseURL },
  });
  expect(response.status(), await response.text()).toBe(200);
  return meetingSpots;
}

// Times render like "4:30 PM" (some locales put a narrow no-break space before PM).
const TIME = /^\d{1,2}:\d{2}\s?[AP]M$/;

/**
 * Picks `count` meetup times in a MeetupPicker, moving to the next day when the current one runs
 * out, and returns their labels. `skip` leaves out that many times at the start, so a reschedule
 * can choose a different time from the first request.
 */
export async function pickMeetupTimes(picker: Locator, count: number, skip = 0) {
  const timeGroup = picker.getByRole("group", { name: /Choose (a time|up to two times)/ });
  const days = timeGroup.getByRole("button", { name: /^[A-Z][a-z]{2}, / });
  // The picker loads the seller's times after it appears.
  await expect(days.first()).toBeVisible();
  const picked: string[] = [];
  let toSkip = skip;
  for (let day = 0; picked.length < count; day += 1) {
    expect(day, "enough meetup times in the picker").toBeLessThan(await days.count());
    await days.nth(day).click();
    const times = timeGroup.getByRole("button", { name: TIME });
    for (let index = 0; index < (await times.count()) && picked.length < count; index += 1) {
      if (toSkip > 0) {
        toSkip -= 1;
        continue;
      }
      await times.nth(index).click();
      picked.push((await times.nth(index).innerText()).trim());
    }
  }
  return picked;
}

/**
 * Sends a request on `listingId` as whoever is signed in to `context`, with the seller's first
 * spot and first open time, through the API. Faster than the listing page when the request
 * itself isn't what's being tested.
 */
export async function requestDeal(
  context: BrowserContext,
  baseURL: string,
  listingId: number,
  body: { kind: "buy_now" } | { kind: "offer"; amount_cents: number } = { kind: "buy_now" },
) {
  const api = context.request;
  const options = await api.get(`/api/listings/${listingId}/meetup-options/`);
  expect(options.ok()).toBe(true);
  const { meeting_spots, slots } = (await options.json()) as {
    meeting_spots: { id: number }[];
    slots: { starts_at: string }[];
  };
  const csrfToken = (await context.cookies()).find((c) => c.name === "csrftoken")?.value;
  const response = await api.post(`/api/listings/${listingId}/deals/`, {
    data: { ...body, meeting_spot_id: meeting_spots[0].id, proposed_starts_at: [slots[0].starts_at] },
    headers: { "X-CSRFToken": csrfToken!, Origin: baseURL },
  });
  expect(response.status(), await response.text()).toBe(201);
}
