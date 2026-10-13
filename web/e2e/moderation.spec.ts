import { randomUUID } from "node:crypto";

import { expect, test } from "@playwright/test";

import { postListing } from "./listings";
import { signIn } from "./sign-in";
import { TEST_BUYER, TEST_MODERATOR, TEST_SECOND_BUYER } from "./test-user";

test("students get the moderators-only page at /moderation", async ({ context, page, baseURL }) => {
  await signIn(context, baseURL!, TEST_BUYER);
  await page.goto("/moderation");
  await expect(page.getByRole("heading", { level: 1, name: "Moderators only" })).toBeVisible();
  const api = await context.request.get("/api/moderation/cases/");
  expect(api.status()).toBe(403);
});

test("a moderator works a case from the queue: warn, restrict and lift, remove and restore, dismiss", async ({ browser, context, page, baseURL }) => {
  // TEST_SECOND_BUYER is the seller here: no other test sells as them, so a short selling
  // restriction can't disturb tests running in parallel.
  const sellerContext = await browser.newContext({ baseURL });
  await signIn(sellerContext, baseURL!, TEST_SECOND_BUYER);
  const title = `E2E moderation knife ${randomUUID().slice(0, 8)}`;
  const listingId = await postListing(sellerContext, baseURL!, { title, category: "electronics" });
  await sellerContext.close();

  const reporterContext = await browser.newContext({ baseURL });
  await signIn(reporterContext, baseURL!, TEST_BUYER);
  const csrf = (await reporterContext.cookies()).find((c) => c.name === "csrftoken")?.value;
  const reported = await reporterContext.request.post("/api/reports/", {
    data: { target_type: "listing", target_id: listingId, reason: "prohibited_item", prohibited_category: "weapon", details: "Sold as a protection knife" },
    headers: { "X-CSRFToken": csrf!, Origin: baseURL! },
  });
  expect(reported.status()).toBe(201);
  await reporterContext.close();

  await signIn(context, baseURL!, TEST_MODERATOR);
  await page.goto("/profile");
  await page.getByRole("link", { name: "Moderation" }).click();
  await expect(page).toHaveURL("/moderation");
  const row = page.getByRole("link").filter({ hasText: title });
  await expect(row).toContainText("Urgent");
  await row.click();

  await expect(page.getByRole("heading", { level: 1 })).toContainText("Prohibited item");
  await expect(page.getByText("“Sold as a protection knife”")).toBeVisible();
  const actions = page.getByRole("complementary", { name: "Actions" });

  async function take(label: string, reason: string) {
    await actions.getByRole("button", { name: label, exact: true }).click();
    await actions.getByLabel(/Internal reason|Note/).fill(reason);
    await actions.getByRole("button", { name: label, exact: true }).last().click();
    await expect(actions.getByRole("status")).toContainText(`${label} saved.`);
  }

  await take("Send warning", "First warning: no weapons on Tanu.");
  await expect(page.getByRole("region", { name: "Activity" })).toContainText("First warning");

  await actions.getByRole("button", { name: "Restrict a feature", exact: true }).click();
  await actions.getByLabel("For").selectOption("3");
  await actions.getByLabel(/Internal reason/).fill("Selling paused while we review.");
  await actions.getByRole("button", { name: "Restrict a feature", exact: true }).last().click();
  await expect(page.getByText("Selling paused while we review.").first()).toBeVisible();
  await page.getByRole("button", { name: "Lift", exact: true }).click();
  await page.getByLabel("Reason for lifting").fill("Review done.");
  await page.getByRole("button", { name: "Lift", exact: true }).last().click();
  await expect(page.getByRole("heading", { name: "Active restrictions" }).locator("xpath=following-sibling::p[1]")).toHaveText("None.");

  await take("Remove listing", "Knives are prohibited.");
  await expect(page.getByText("now removed (by moderation)")).toBeVisible();
  await take("Restore listing", "Turned out to be a butter knife set.");
  await expect(page.getByText("now available")).toBeVisible();

  await take("Dismiss: no violation", "No violation after review.");
  await expect(page.getByText("resolved", { exact: true })).toBeVisible();
});

test("students get notices, can appeal, and answer a moderator's question", async ({ browser, context, page, baseURL }) => {
  const token = randomUUID().slice(0, 8);
  const sellerContext = await browser.newContext({ baseURL });
  await signIn(sellerContext, baseURL!, TEST_SECOND_BUYER);
  const title = `E2E appeal lamp ${token}`;
  const listingId = await postListing(sellerContext, baseURL!, { title, category: "electronics" });

  const reporterContext = await browser.newContext({ baseURL });
  await signIn(reporterContext, baseURL!, TEST_BUYER);
  const csrf = (await reporterContext.cookies()).find((c) => c.name === "csrftoken")?.value;
  expect((await reporterContext.request.post("/api/reports/", {
    data: { target_type: "listing", target_id: listingId, reason: "counterfeit" },
    headers: { "X-CSRFToken": csrf!, Origin: baseURL! },
  })).status()).toBe(201);

  // The moderator asks the reporter a question and warns the seller in their own words.
  await signIn(context, baseURL!, TEST_MODERATOR);
  await page.goto("/moderation");
  await page.getByRole("link").filter({ hasText: title }).click();
  const actions = page.getByRole("complementary", { name: "Actions" });
  await actions.getByRole("button", { name: "Ask for more information", exact: true }).click();
  const reporterId = String(((await (await reporterContext.request.get("/api/me/")).json()) as { id: number }).id);
  await actions.getByRole("combobox", { name: "Student" }).selectOption(reporterId);
  await actions.getByLabel(/Question/).fill(`Where did you see it? ${token}`);
  await actions.getByRole("button", { name: "Ask for more information", exact: true }).last().click();
  await expect(actions.getByRole("status")).toContainText("saved");

  await actions.getByRole("button", { name: "Send warning", exact: true }).click();
  await actions.getByLabel(/Message to the student/).fill(`Please only list genuine items. ${token}`);
  await actions.getByLabel(/Internal reason/).fill("Likely counterfeit.");
  await actions.getByRole("button", { name: "Send warning", exact: true }).last().click();
  await expect(actions.getByRole("status")).toContainText("saved");

  // The seller sees it in their notifications and appeals from Account status.
  const sellerPage = await sellerContext.newPage();
  await sellerPage.goto("/");
  await expect(sellerPage.getByRole("link", { name: /Notifications, \d+ unread/ })).toBeVisible();
  await sellerPage.getByRole("link", { name: /Notifications/ }).click();
  const notice = sellerPage.getByRole("link").filter({ hasText: `Please only list genuine items. ${token}` });
  await expect(notice).toContainText("A warning from Tanu's moderators");
  await notice.click();
  await expect(sellerPage).toHaveURL("/profile/standing");
  const decision = sellerPage.getByRole("listitem").filter({ hasText: token });
  await decision.getByRole("button", { name: /Appeal this decision/ }).click();
  await decision.getByLabel("Why should we look at this again?").fill(`It's genuine, I have the receipt. ${token}`);
  await decision.getByRole("button", { name: "Send appeal" }).click();
  await expect(decision).toContainText("being reviewed by a different moderator");

  // The reporter answers the question.
  const reporterPage = await reporterContext.newPage();
  await reporterPage.goto("/profile/standing");
  const question = reporterPage.getByRole("listitem").filter({ hasText: `Where did you see it? ${token}` });
  await question.getByLabel("Your answer").fill("On the listing page, yesterday.");
  await question.getByRole("button", { name: "Send answer" }).click();
  await expect(reporterPage.getByText(`Where did you see it? ${token}`)).toHaveCount(0);

  // Back on the case: the appeal and the answer are there.
  await page.reload();
  await expect(page.getByRole("region", { name: "Appeals" })).toContainText(`I have the receipt. ${token}`);
  await expect(page.getByRole("region", { name: "Questions to students" })).toContainText("On the listing page, yesterday.");

  await sellerContext.close();
  await reporterContext.close();
});

test("moderators see stats; students don't", async ({ browser, context, page, baseURL }) => {
  await signIn(context, baseURL!, TEST_MODERATOR);
  await page.goto("/moderation");
  await page.getByRole("link", { name: "Stats" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Moderation stats" })).toBeVisible();
  await expect(page.getByText("Cases opened", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Last 90 days" }).click();
  await expect(page.getByRole("button", { name: "Last 90 days" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("region", { name: "Reports by reason" })).toBeVisible();

  const studentContext = await browser.newContext({ baseURL });
  await signIn(studentContext, baseURL!, TEST_BUYER);
  const studentPage = await studentContext.newPage();
  await studentPage.goto("/moderation/stats");
  await expect(studentPage.getByRole("heading", { level: 1, name: "Moderators only" })).toBeVisible();
  await studentContext.close();
});
