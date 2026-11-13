import { randomUUID } from "node:crypto";

import { expect, test, type Page } from "@playwright/test";

import { postListing } from "./listings";
import { requestDeal, setMeetupPreferences } from "./meetups";
import { signIn } from "./sign-in";
import { TEST_BUYER, TEST_USER } from "./test-user";

const strip = (page: Page) => page.getByRole("link", { name: /deals? needs? you/ });

test("a guest gets the welcome page with the footer", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Your campus is a closet." })).toBeVisible();
  await expect(page.getByRole("contentinfo")).toContainText("not affiliated with or endorsed by any university");
  await expect(strip(page)).toHaveCount(0);
});

test("a student's Home is their school's feed, with Filters on Search", async ({ browser, context, page, baseURL }) => {
  await signIn(context, baseURL!, TEST_BUYER);
  const title = `E2E home feed lamp ${randomUUID().slice(0, 8)}`;
  const sellerContext = await browser.newContext({ baseURL });
  await signIn(sellerContext, baseURL!, TEST_USER);
  await postListing(sellerContext, baseURL!, { title, category: "electronics" });
  await sellerContext.close();

  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "New at UMD" })).toBeVisible();
  await expect(page.getByRole("list", { name: "Listings" }).getByText(title)).toBeVisible();
  // No filter row and no footer on Home; Filters opens Search.
  await expect(page.getByRole("button", { name: "Price" })).toHaveCount(0);
  await expect(page.getByRole("contentinfo")).toHaveCount(0);
  await page.getByRole("link", { name: "Filters" }).click();
  await expect(page).toHaveURL("/search");
});

// The strip's wording for each kind of deal, on a fixed clock with the deals list served by the
// test (other tests give the shared students real deals at the same time).
const NOW = "2026-11-12T15:00:00-05:00"; // a Thursday, 3:00 PM campus time
const ME = 1;
const OTHER = 2;
const at = (time: string) => new Date(time).toISOString();
const deal = (fields: Record<string, unknown>) => ({
  section: "current", status: "awaiting_seller", my_role: "seller", awaiting_me: false,
  response_deadline: null, handoff_deadline: null, buyer_confirmed: false, seller_confirmed: false,
  seller: { id: ME }, buyer: { id: OTHER }, meetup_proposals: [], ...fields,
});
const meetupAt = (time: string) => [{ status: "accepted", starts_at: at(time), proposed_by: { id: OTHER } }];
const newTime = (time: string, by: number) => ({ status: "pending", starts_at: at(time), proposed_by: { id: by } });
const toAnswer = (deadline: string) => deal({ awaiting_me: true, response_deadline: at(deadline) });
const handoff = (fields: Record<string, unknown>) => deal({ status: "pending", handoff_deadline: at("2026-11-14T10:00:00-05:00"), ...fields });
// Nothing here waits on the viewer: the other side's turn, a meetup tomorrow, a request whose 24h
// is up, a handoff the viewer already confirmed, a new time the viewer proposed, a new time from
// the other side that has already passed, and a finished deal.
const NOT_WAITING = [
  deal({ status: "awaiting_buyer", response_deadline: at("2026-11-13T09:00:00-05:00") }),
  handoff({ meetup_proposals: meetupAt("2026-11-13T12:00:00-05:00") }),
  toAnswer("2026-11-12T14:00:00-05:00"),
  handoff({ seller_confirmed: true, meetup_proposals: meetupAt("2026-11-12T10:00:00-05:00") }),
  handoff({ meetup_proposals: [...meetupAt("2026-11-13T12:00:00-05:00"), newTime("2026-11-13T17:00:00-05:00", ME)] }),
  handoff({ meetup_proposals: [...meetupAt("2026-11-13T12:00:00-05:00"), newTime("2026-11-12T14:00:00-05:00", OTHER)] }),
  deal({ section: "history", status: "completed" }),
];

test("the strip counts the deals waiting on you and names the nearest deadline", async ({ context, page, baseURL }) => {
  await signIn(context, baseURL!, TEST_BUYER);
  await page.clock.setFixedTime(new Date(NOW));
  let served: unknown[] = [];
  await page.route((url) => url.pathname === "/api/deals/", (route) => route.fulfill({ json: served }));

  const cases: { deals: unknown[]; title?: string; detail?: string }[] = [
    { deals: NOT_WAITING },
    { deals: [...NOT_WAITING, toAnswer("2026-11-12T17:00:00-05:00")], title: "A deal needs you", detail: "Answer by today at 5:00 PM" },
    { deals: [toAnswer("2026-11-13T09:00:00-05:00"), toAnswer("2026-11-12T17:00:00-05:00")], title: "2 deals need you", detail: "Answer the first by today at 5:00 PM" },
    { deals: [handoff({ meetup_proposals: meetupAt("2026-11-12T18:00:00-05:00") })], title: "A deal needs you", detail: "Meetup today at 6:00 PM" },
    // The meetup time has passed and nobody confirmed: confirm before the handoff lapses.
    { deals: [handoff({ meetup_proposals: meetupAt("2026-11-12T10:00:00-05:00") })], title: "A deal needs you", detail: "Confirm the handoff by Sat 10:00 AM" },
    { deals: [handoff({ buyer_confirmed: true, meetup_proposals: meetupAt("2026-11-13T12:00:00-05:00") })], title: "A deal needs you", detail: "Confirm the handoff by Sat 10:00 AM" },
    // The other side proposed a new time after the first one passed: answer it, not "confirm".
    { deals: [handoff({ meetup_proposals: [...meetupAt("2026-11-12T10:00:00-05:00"), newTime("2026-11-13T17:00:00-05:00", OTHER)] })], title: "A deal needs you", detail: "Answer the new meetup time" },
    { deals: [toAnswer("2026-11-13T09:00:00-05:00"), handoff({ buyer_confirmed: true })], title: "2 deals need you", detail: "Next deadline Fri 9:00 AM" },
  ];
  for (const { deals, title, detail } of cases) {
    served = deals;
    const loaded = page.waitForResponse((response) => new URL(response.url()).pathname === "/api/deals/");
    await page.goto("/");
    await loaded;
    await expect(page.getByRole("heading", { level: 1, name: "New at UMD" })).toBeVisible();
    if (!title) {
      await expect(strip(page), "nothing waiting").toHaveCount(0);
      continue;
    }
    await expect(strip(page), detail).toContainText(title);
    await expect(strip(page), detail).toContainText(detail!);
  }
});

test("an expired session on Home shows the guest page", async ({ context, page, baseURL }) => {
  // A session cookie the API doesn't recognize: Home starts as the feed, then finds out.
  await context.addCookies([{ name: "sessionid", value: "expired-session", url: baseURL! }]);
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Your campus is a closet." })).toBeVisible();
  await expect(page.getByRole("contentinfo")).toContainText("not affiliated with or endorsed by any university");
});

test("a request to answer shows the strip, which opens Deals", async ({ browser, context, page, baseURL }) => {
  await signIn(context, baseURL!, TEST_USER);
  await setMeetupPreferences(context, baseURL!);
  const listingId = await postListing(context, baseURL!, { title: `E2E strip lamp ${randomUUID().slice(0, 8)}`, category: "electronics" });
  const buyerContext = await browser.newContext({ baseURL });
  await signIn(buyerContext, baseURL!, TEST_BUYER);
  await requestDeal(buyerContext, baseURL!, listingId);
  await buyerContext.close();

  await page.goto("/");
  // Other tests may leave more requests waiting, so the count isn't fixed.
  await expect(strip(page)).toBeVisible();
  await expect(strip(page)).toContainText(/Answer (the first )?by|Meetup today|Next deadline|Confirm the handoff/);
  await strip(page).click();
  await expect(page).toHaveURL("/deals");
});
