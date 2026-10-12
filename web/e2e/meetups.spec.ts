import { randomUUID } from "node:crypto";

import { expect, test, type Browser, type BrowserContext, type Page } from "@playwright/test";

import { postListing } from "./listings";
import { pickMeetupTimes, requestDeal, setMeetupPreferences } from "./meetups";
import { signIn } from "./sign-in";
import { TEST_BUYER, TEST_SECOND_BUYER, TEST_USER } from "./test-user";

// Run in a browser far from campus: every date and time must still show in campus time, so the
// picker, the deal cards, and the other person all agree on when the meetup is.
const AWAY_FROM_CAMPUS = "America/Los_Angeles";
test.use({ timezoneId: AWAY_FROM_CAMPUS });

/** The seller (TEST_USER) posts a listing with meetup preferences; TEST_BUYER gets a page. */
async function sellerAndBuyer(browser: Browser, context: BrowserContext, baseURL: string) {
  await signIn(context, baseURL);
  const spots = await setMeetupPreferences(context, baseURL);
  // Shared students across tests and retries, so each run finds its deal by a fresh title.
  const title = `E2E bike lock ${randomUUID().slice(0, 8)}`;
  const listingId = await postListing(context, baseURL, { title, category: "electronics", priceCents: 3000 });

  const buyerContext = await browser.newContext({ baseURL, timezoneId: AWAY_FROM_CAMPUS });
  await signIn(buyerContext, baseURL, TEST_BUYER);
  const buyerPage = await buyerContext.newPage();
  return { spots, title, listingId, buyerContext, buyerPage };
}

function dealCard(page: Page, title: string) {
  return page.getByRole("article").filter({ hasText: title });
}

async function openDeals(page: Page, role: "Buying" | "Selling") {
  await page.goto("/deals");
  await page.getByRole("tab", { name: new RegExp(`^${role}`) }).click();
}

test("buy now carries a meetup, the seller's accept confirms it, and a reschedule needs the other side", async ({
  browser,
  context,
  page,
  baseURL,
}) => {
  const { spots, title, listingId, buyerContext, buyerPage } = await sellerAndBuyer(browser, context, baseURL!);

  // The buyer picks a campus spot and a time as part of Buy now.
  await buyerPage.goto(`/listings/${listingId}`);
  await buyerPage.getByRole("button", { name: "Buy now" }).click();
  await expect(buyerPage.getByRole("group", { name: "Choose a safe campus location" })).toBeVisible();
  await expect(buyerPage.getByRole("button", { name: new RegExp(spots[0].name) })).toHaveAttribute("aria-pressed", "true");
  const [time] = await pickMeetupTimes(buyerPage.locator("body"), 1);
  await buyerPage.getByRole("button", { name: "Send request" }).click();
  await expect(buyerPage).toHaveURL("/deals");
  await expect(dealCard(buyerPage, title)).toContainText(`Waiting for @${TEST_USER.username} to respond to your proposed meetup`);
  await expect(dealCard(buyerPage, title)).toContainText(time);

  // The seller sees the proposed meetup and accepting confirms it.
  await openDeals(page, "Selling");
  const sellerCard = dealCard(page, title);
  await expect(sellerCard.getByRole("group", { name: "Proposed meetup" })).toContainText(spots[0].name);
  await sellerCard.getByRole("button", { name: "Accept", exact: true }).click();
  await expect(sellerCard).toContainText("Handoff pending");
  await expect(sellerCard).toContainText(spots[0].name);
  await expect(sellerCard).not.toContainText("Meetup time still needs to be confirmed");

  // The buyer asks to move it. The original stays confirmed until the seller agrees.
  await openDeals(buyerPage, "Buying");
  const buyerCard = dealCard(buyerPage, title);
  await buyerCard.getByRole("button", { name: "Reschedule" }).click();
  await expect(buyerCard).toContainText("The current meetup stays confirmed");
  const [newTime] = await pickMeetupTimes(buyerCard, 1, 2);
  await buyerCard.getByRole("button", { name: "Send change" }).click();
  await expect(buyerCard).toContainText(`Waiting for @${TEST_USER.username} to respond to your proposed meetup`);
  await expect(buyerCard).toContainText(newTime);

  await page.reload();
  await page.getByRole("tab", { name: /^Selling/ }).click();
  await expect(sellerCard).toContainText("New meetup proposed");
  await sellerCard.getByRole("button", { name: "Accept new meetup" }).click();
  await expect(sellerCard).not.toContainText("New meetup proposed");
  await expect(sellerCard).toContainText(newTime);

  // On the day, either side can say they've arrived.
  await sellerCard.getByRole("button", { name: "I'm here" }).click();
  await expect(sellerCard).toContainText(`@${TEST_USER.username} is here.`);

  await buyerContext.close();
});

test("an offer with two times: the seller keeps one with a counter, and the buyer's accept confirms it", async ({
  browser,
  context,
  page,
  baseURL,
}) => {
  const { title, listingId, buyerContext, buyerPage } = await sellerAndBuyer(browser, context, baseURL!);

  await buyerPage.goto(`/listings/${listingId}`);
  await buyerPage.getByRole("button", { name: "Make offer" }).click();
  await buyerPage.getByLabel("Offer amount").fill("20");
  const times = await pickMeetupTimes(buyerPage.locator("body"), 2);
  await buyerPage.getByRole("button", { name: "Send request" }).click();
  await expect(buyerPage).toHaveURL("/deals");

  // The seller chooses which of the two times to keep, then counters on price.
  await openDeals(page, "Selling");
  const sellerCard = dealCard(page, title);
  const choices = sellerCard.getByRole("group", { name: "Choose a meetup time" });
  await expect(choices.getByRole("button")).toHaveCount(2);
  // Times are listed earliest first, so this keeps the buyer's second choice.
  await choices.getByRole("button").nth(1).click();
  await sellerCard.getByRole("button", { name: "Counter", exact: true }).click();
  await sellerCard.getByLabel("Counteroffer amount").fill("25");
  await sellerCard.getByRole("button", { name: "Send counter" }).click();
  await expect(sellerCard).toContainText("Waiting for buyer");

  // Accepting the counter confirms the kept time with no extra step.
  await openDeals(buyerPage, "Buying");
  const buyerCard = dealCard(buyerPage, title);
  await expect(buyerCard).toContainText("Seller countered");
  await buyerCard.getByRole("button", { name: "Accept", exact: true }).click();
  await expect(buyerCard).toContainText("Handoff pending");
  await expect(buyerCard).toContainText("$25");
  await expect(buyerCard).not.toContainText("Meetup time still needs to be confirmed");
  // The deal card shows the date as "Oct 13, 5:30 PM"; the picker showed just "5:30 PM".
  await expect(buyerCard).toContainText(times[1]);

  await buyerContext.close();
});

test("a seller can split a day into several meetup ranges, but not overlapping ones", async ({
  context,
  page,
  baseURL,
}) => {
  // TEST_BUYER, because the deal tests rely on TEST_USER's all-day availability.
  await signIn(context, baseURL!, TEST_BUYER);
  await page.goto("/profile/meetup");
  await expect(page.getByRole("heading", { level: 1, name: "Meetup preferences" })).toBeVisible();

  const firstSpot = page.getByRole("checkbox").first();
  await firstSpot.check();
  const monday = page.getByRole("checkbox", { name: "Monday" });
  await monday.check();
  await page.getByLabel("Monday start time 1").fill("10:00");
  await page.getByLabel("Monday end time 1").fill("11:00");
  await page.getByRole("button", { name: "+ Add another time" }).click();
  await page.getByLabel("Monday start time 2").fill("15:00");
  await page.getByLabel("Monday end time 2").fill("17:00");
  await page.getByRole("button", { name: "Save meetup preferences" }).click();
  await expect(page.getByRole("status")).toHaveText("Meetup preferences saved.");

  await page.reload();
  await expect(page.getByLabel("Monday start time 1")).toHaveValue("10:00");
  await expect(page.getByLabel("Monday start time 2")).toHaveValue("15:00");
  await expect(page.getByLabel("Monday end time 2")).toHaveValue("17:00");

  await page.getByLabel("Monday start time 2").fill("10:30");
  await page.getByRole("button", { name: "Save meetup preferences" }).click();
  await expect(page.getByText("Your Monday time ranges overlap.")).toBeVisible();

  await page.getByRole("button", { name: "Remove Monday time range 2" }).click();
  await expect(page.getByLabel("Monday start time 2")).toHaveCount(0);
});

test("when it's the seller's turn, suggesting another time hands the request back to the buyer", async ({
  browser,
  context,
  page,
  baseURL,
}) => {
  const { title, listingId, buyerContext, buyerPage } = await sellerAndBuyer(browser, context, baseURL!);
  await requestDeal(buyerContext, baseURL!, listingId);

  await openDeals(page, "Selling");
  const sellerCard = dealCard(page, title);
  await sellerCard.getByRole("button", { name: "Suggest another time" }).click();
  await expect(sellerCard).toContainText("This replaces the proposed times");
  const [newTime] = await pickMeetupTimes(sellerCard, 1, 3);
  await sellerCard.getByRole("button", { name: "Send change" }).click();
  await expect(sellerCard).toContainText("Waiting for buyer");
  await expect(sellerCard).toContainText(newTime);

  await openDeals(buyerPage, "Buying");
  const buyerCard = dealCard(buyerPage, title);
  await expect(buyerCard.getByRole("group", { name: "Proposed meetup" })).toContainText(newTime);
  await buyerCard.getByRole("button", { name: "Accept", exact: true }).click();
  await expect(buyerCard).toContainText("Handoff pending");
  await expect(buyerCard).toContainText(newTime);
  await expect(buyerCard).not.toContainText("Meetup time still needs to be confirmed");

  await buyerContext.close();
});

test("a declined request and a canceled purchase both leave the listing available", async ({
  browser,
  context,
  page,
  baseURL,
}) => {
  const { title, listingId, buyerContext, buyerPage } = await sellerAndBuyer(browser, context, baseURL!);

  // The seller declines the first request.
  await requestDeal(buyerContext, baseURL!, listingId, { kind: "offer", amount_cents: 1000 });
  await openDeals(page, "Selling");
  await dealCard(page, title).getByRole("button", { name: "Decline" }).click();
  await page.getByRole("heading", { name: "Closed offers" }).click();
  await expect(dealCard(page, title)).toContainText("Declined");

  // The buyer tries again, the seller accepts, then the buyer backs out. The declined request
  // has the same title, so these cards leave it out.
  await buyerPage.goto(`/listings/${listingId}`);
  await expect(buyerPage.getByRole("button", { name: "Buy now" })).toBeEnabled();
  await requestDeal(buyerContext, baseURL!, listingId);
  await page.reload();
  await page.getByRole("tab", { name: /^Selling/ }).click();
  const sellerCard = dealCard(page, title).filter({ hasNotText: "Declined" });
  await sellerCard.getByRole("button", { name: "Accept", exact: true }).click();
  await expect(sellerCard).toContainText("Handoff pending");

  await openDeals(buyerPage, "Buying");
  const buyerCard = dealCard(buyerPage, title).filter({ hasNotText: "Declined" });
  await buyerCard.getByRole("button", { name: "Cancel purchase" }).click();
  // Canceled deals move into the collapsed Closed offers section.
  await buyerPage.getByRole("heading", { name: "Closed offers" }).click();
  await expect(dealCard(buyerPage, title).filter({ hasText: "Canceled" })).toBeVisible();

  await buyerPage.goto(`/listings/${listingId}`);
  await expect(buyerPage.getByRole("button", { name: "Buy now" })).toBeEnabled();
  await buyerContext.close();
});

test("a second buyer waits as a backup and the seller can choose them when the first backs out", async ({
  browser,
  context,
  page,
  baseURL,
}) => {
  const { title, listingId, buyerContext, buyerPage } = await sellerAndBuyer(browser, context, baseURL!);
  const secondContext = await browser.newContext({ baseURL, timezoneId: AWAY_FROM_CAMPUS });
  await signIn(secondContext, baseURL!, TEST_SECOND_BUYER);
  const secondPage = await secondContext.newPage();
  await requestDeal(buyerContext, baseURL!, listingId);
  await requestDeal(secondContext, baseURL!, listingId);

  // Usernames overlap (e2e_buyer, e2e_buyer_two), so match the buyer link exactly.
  const cardFor = (username: string) =>
    dealCard(page, title).filter({ has: page.getByRole("link", { name: `@${username}`, exact: true }) });

  await openDeals(page, "Selling");
  await cardFor(TEST_BUYER.username).getByRole("button", { name: "Accept", exact: true }).click();
  await expect(cardFor(TEST_BUYER.username)).toContainText("Handoff pending");
  await expect(cardFor(TEST_SECOND_BUYER.username)).toContainText("Available as a backup");

  await openDeals(secondPage, "Buying");
  await expect(dealCard(secondPage, title)).toContainText("Backup buyer");

  // The first buyer backs out; the listing is free again and the seller picks the backup,
  // which confirms the backup's proposed meetup too.
  await openDeals(buyerPage, "Buying");
  await dealCard(buyerPage, title).getByRole("button", { name: "Cancel purchase" }).click();
  await page.reload();
  await page.getByRole("tab", { name: /^Selling/ }).click();
  const backup = cardFor(TEST_SECOND_BUYER.username);
  await backup.getByRole("button", { name: "Choose buyer" }).click();
  await expect(backup).toContainText("Handoff pending");
  await expect(backup).not.toContainText("Meetup time still needs to be confirmed");

  await secondContext.close();
  await buyerContext.close();
});
