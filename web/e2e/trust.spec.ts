import { randomUUID } from "node:crypto";

import { expect, test } from "@playwright/test";

import { postListing } from "./listings";
import { signIn } from "./sign-in";
import { TEST_BUYER, TEST_SECOND_BUYER, TEST_USER } from "./test-user";

test("a student reports a listing as a weapon and only gets a receipt", async ({ browser, context, baseURL }) => {
  await signIn(context, baseURL!);
  const title = `E2E report lamp ${randomUUID().slice(0, 8)}`;
  const listingId = await postListing(context, baseURL!, { title, category: "electronics" });

  const reporterContext = await browser.newContext({ baseURL });
  await signIn(reporterContext, baseURL!, TEST_BUYER);
  const page = await reporterContext.newPage();
  await page.goto(`/listings/${listingId}`);

  await page.getByRole("button", { name: "Report listing" }).click();
  const dialog = page.getByRole("dialog", { name: "Report this listing" });
  await dialog.getByRole("radio", { name: "Prohibited item" }).check();
  await dialog.getByLabel("What kind of item?").selectOption("weapon");
  await dialog.getByLabel(/Anything else/).fill("Listed as a 'protection knife'.");
  await dialog.getByRole("button", { name: "Send report" }).click();
  await expect(page.getByRole("dialog", { name: "Report received" })).toContainText("moderation team will review it");
  await page.getByRole("button", { name: "Done" }).click();

  // A second report of the same listing is turned away.
  await page.getByRole("button", { name: "Report listing" }).click();
  await page.getByRole("radio", { name: "Counterfeit item" }).check();
  await page.getByRole("button", { name: "Send report" }).click();
  await expect(page.getByRole("dialog").getByRole("alert")).toContainText("already reported");
  await reporterContext.close();
});

test("reporting a conversation sends only the chosen messages and can block the sender", async ({ browser, context, page, baseURL }) => {
  // TEST_SECOND_BUYER sends the messages, so blocking doesn't affect the other tests' students.
  const senderContext = await browser.newContext({ baseURL });
  await signIn(senderContext, baseURL!, TEST_SECOND_BUYER);
  const csrf = (await senderContext.cookies()).find((c) => c.name === "csrftoken")?.value;
  const headers = { "X-CSRFToken": csrf!, Origin: baseURL! };
  const started = await senderContext.request.post("/api/conversations/", { data: { username: TEST_USER.username }, headers });
  const conversationId = ((await started.json()) as { id: number }).id;
  const rude = `you'll regret it ${randomUUID().slice(0, 6)}`;
  for (const body of ["hey, still selling?", rude]) {
    expect((await senderContext.request.post(`/api/conversations/${conversationId}/messages/`, { data: { body }, headers })).ok()).toBe(true);
  }

  await signIn(context, baseURL!);
  await page.goto(`/inbox/${conversationId}`);
  await page.getByRole("button", { name: "Report" }).click();
  const dialog = page.getByRole("dialog", { name: "Report this conversation" });
  await dialog.getByRole("radio", { name: "Harassment" }).check();
  await expect(dialog).toContainText("call 911");
  await dialog.getByRole("button", { name: "Send report" }).click();
  await expect(dialog.getByRole("alert")).toContainText("Choose the messages");
  await dialog.getByRole("checkbox", { name: new RegExp(rude) }).check();
  await dialog.getByRole("checkbox", { name: `Also block @${TEST_SECOND_BUYER.username}` }).check();
  await dialog.getByRole("button", { name: "Send report" }).click();
  await expect(page.getByRole("dialog", { name: "Report received" })).toContainText(`blocked @${TEST_SECOND_BUYER.username}`);
  await page.getByRole("button", { name: "Done" }).click();

  // Neither side can message the other now; the sender isn't told why.
  const reply = await senderContext.request.post(`/api/conversations/${conversationId}/messages/`, { data: { body: "hello?" }, headers });
  expect(reply.status()).toBe(400);
  expect(JSON.stringify(await reply.json())).toContain("isn't available");

  // Unblocking from their profile restores messaging.
  await page.goto(`/users/${TEST_SECOND_BUYER.username}`);
  await page.getByRole("button", { name: "Unblock" }).click();
  await expect(page.getByRole("button", { name: "Block", exact: true })).toBeVisible();
  const again = await senderContext.request.post(`/api/conversations/${conversationId}/messages/`, { data: { body: "sorry" }, headers });
  expect(again.ok()).toBe(true);
  await senderContext.close();
});

test("blocking from a profile asks first", async ({ context, page, baseURL }) => {
  await signIn(context, baseURL!, TEST_SECOND_BUYER);
  await page.goto(`/users/${TEST_BUYER.username}`);
  await page.getByRole("button", { name: "Block", exact: true }).click();
  await expect(page.getByText(`Block @${TEST_BUYER.username}?`)).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByRole("button", { name: "Block", exact: true })).toBeVisible();
});
