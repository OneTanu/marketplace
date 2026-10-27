import { randomUUID } from "node:crypto";

import { expect, test, type BrowserContext, type Page } from "@playwright/test";

import { postListing } from "./listings";
import { requestDeal, setMeetupPreferences } from "./meetups";
import { signIn } from "./sign-in";
import { TEST_BUYER, TEST_MODERATOR, TEST_USER } from "./test-user";

function dealCard(page: Page, title: string) {
  return page.getByRole("article").filter({ hasText: title });
}

async function openDeals(page: Page, role: "Buying" | "Selling") {
  await page.goto("/deals");
  await page.getByRole("tab", { name: new RegExp(`^${role}`) }).click();
}

/** The seller posts a listing; the buyer asks to buy it; the seller accepts. */
async function pendingDeal(sellerContext: BrowserContext, buyerContext: BrowserContext, sellerPage: Page, baseURL: string) {
  await setMeetupPreferences(sellerContext, baseURL);
  const title = `E2E dispute ${randomUUID().slice(0, 8)}`;
  const listingId = await postListing(sellerContext, baseURL, { title, category: "electronics", priceCents: 4000 });
  await requestDeal(buyerContext, baseURL, listingId);
  await openDeals(sellerPage, "Selling");
  await dealCard(sellerPage, title).getByRole("button", { name: "Accept", exact: true }).click();
  await expect(dealCard(sellerPage, title)).toContainText("Handoff pending");
  return { title, listingId };
}

test("conflicting handoff reports go to a moderator, who decides; the listing waits", async ({ browser, context, page, baseURL }) => {
  await signIn(context, baseURL!, TEST_USER);
  const buyerContext = await browser.newContext({ baseURL });
  await signIn(buyerContext, baseURL!, TEST_BUYER);
  const buyerPage = await buyerContext.newPage();
  const { title, listingId } = await pendingDeal(context, buyerContext, page, baseURL!);

  // The buyer confirms the handoff.
  await openDeals(buyerPage, "Buying");
  const buyerCard = dealCard(buyerPage, title);
  await buyerCard.getByRole("button", { name: "Confirm handoff" }).click();
  await expect(buyerCard).toContainText("You confirmed");

  // The seller can't cancel now; they report a payment problem instead.
  await page.reload();
  await page.getByRole("tab", { name: /^Selling/ }).click();
  const sellerCard = dealCard(page, title);
  await expect(sellerCard.getByRole("button", { name: /^Cancel/ })).toHaveCount(0);
  await sellerCard.getByRole("button", { name: "Report a problem" }).click();
  const form = sellerCard.getByRole("group", { name: "Report a problem" });
  await expect(form).toContainText("a moderator will review it");
  await form.getByLabel("What happened?").selectOption("payment");
  await form.getByLabel(/Details/).fill("They left without paying.");
  await form.getByRole("button", { name: "Send report" }).click();
  await expect(sellerCard).toContainText("Under review by Tanu");
  await expect(sellerCard.getByRole("button", { name: "Confirm handoff" })).toHaveCount(0);

  // Still on hold: nobody else can request it, and it isn't sold.
  const listing = await buyerContext.request.get(`/api/listings/${listingId}/`);
  expect(((await listing.json()) as { status: string }).status).toBe("pending");

  // A moderator finds the dispute and decides the handoff happened.
  const moderatorContext = await browser.newContext({ baseURL });
  await signIn(moderatorContext, baseURL!, TEST_MODERATOR);
  const moderatorPage = await moderatorContext.newPage();
  const cases = (await (await moderatorContext.request.get("/api/moderation/cases/")).json()) as { id: number }[];
  let caseId: number | undefined;
  for (const row of cases) {
    const detail = (await (await moderatorContext.request.get(`/api/moderation/cases/${row.id}/`)).json()) as { deal_disputes: { listing_title: string }[] };
    if (detail.deal_disputes.some((dispute) => dispute.listing_title === title)) caseId = row.id;
  }
  expect(caseId, "a case holding the dispute").toBeDefined();
  await moderatorPage.goto(`/moderation/cases/${caseId}`);
  const disputes = moderatorPage.getByRole("region", { name: "Disputed handoffs" });
  const item = disputes.getByRole("listitem").filter({ hasText: title });
  await expect(item).toContainText("A problem was reported after a confirmation");
  await expect(item).toContainText("“They left without paying.”");
  await item.getByLabel("Dispute decision reason").fill("Messages show payment was made.");
  await item.getByRole("button", { name: "It happened: mark Sold" }).click();
  await expect(item).toContainText("the handoff happened");

  // Both students see it completed and in their Transaction history.
  await buyerPage.reload();
  await buyerPage.getByRole("tab", { name: /^Buying/ }).click();
  const history = buyerPage.getByRole("heading", { name: "Transaction history" }).locator("xpath=ancestor::section[1]");
  await expect(history.getByRole("article").filter({ hasText: title })).toContainText("decided it happened");
  const sold = await buyerContext.request.get(`/api/listings/${listingId}/`);
  expect(((await sold.json()) as { status: string }).status).toBe("sold");

  await moderatorContext.close();
  await buyerContext.close();
});

test("a no-show before any confirmation frees the listing; closed deals can be archived", async ({ browser, context, page, baseURL }) => {
  await signIn(context, baseURL!, TEST_USER);
  const buyerContext = await browser.newContext({ baseURL });
  await signIn(buyerContext, baseURL!, TEST_BUYER);
  const { title, listingId } = await pendingDeal(context, buyerContext, page, baseURL!);

  const card = dealCard(page, title);
  await card.getByRole("button", { name: "Report a problem" }).click();
  const form = card.getByRole("group", { name: "Report a problem" });
  await expect(form).toContainText("ends this deal and makes the item available again");
  await form.getByRole("button", { name: "Send report" }).click();

  // Into Cancelled, and the listing is available again.
  await page.getByRole("heading", { name: "Cancelled" }).click();
  const cancelled = dealCard(page, title);
  await expect(cancelled).toContainText("no-show reported");
  const listing = await context.request.get(`/api/listings/${listingId}/`);
  expect(((await listing.json()) as { status: string }).status).toBe("available");

  // Archive it, and back.
  await cancelled.getByRole("button", { name: "Archive" }).click();
  await page.getByRole("heading", { name: "Archived" }).click();
  const archived = page.getByRole("heading", { name: "Archived" }).locator("xpath=ancestor::details[1]");
  await expect(archived.getByRole("article").filter({ hasText: title })).toBeVisible();
  await archived.getByRole("article").filter({ hasText: title }).getByRole("button", { name: "Move back to Cancelled" }).click();
  await expect(archived.getByRole("article").filter({ hasText: title })).toHaveCount(0);

  await buyerContext.close();
});
