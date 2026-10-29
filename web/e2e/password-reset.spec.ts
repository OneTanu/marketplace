import { expect, test } from "@playwright/test";

import { linkInEmail } from "./email";
import { AUTH, signIn } from "./sign-in";
import { TEST_RESET_USER } from "./test-user";

const RESET_LINK = /https?:\/\/\S+\/account\/password\/reset\/[\w-]+/;
const NEW_PASSWORD = "e2e-reset-new-password-123";

test("resets a forgotten password from the emailed link", async ({ browser, page, baseURL }) => {
  // Another browser where the student is already signed in; the reset should sign it out.
  const otherDevice = await browser.newContext();
  await signIn(otherDevice, baseURL!, TEST_RESET_USER);
  expect((await otherDevice.request.get(`${AUTH}/auth/session`)).status()).toBe(200);

  await page.goto("/account/login");
  await page.getByRole("link", { name: "Forgot password?" }).click();
  await expect(page).toHaveURL(/\/account\/forgot-password$/);
  await expect(page.getByRole("heading", { level: 1, name: "Forgot your password?" })).toBeVisible();

  const email = page.getByLabel("School email");
  await expect(email).toHaveAttribute("autocomplete", "email");
  await email.fill(TEST_RESET_USER.email);
  await page.getByRole("button", { name: "Send reset link" }).click();
  await expect(page.getByRole("status")).toContainText(`If ${TEST_RESET_USER.email} belongs to a Tanu account`);

  await page.goto(await linkInEmail(TEST_RESET_USER.email, RESET_LINK));
  const resetPath = new URL(page.url()).pathname;
  await expect(page.getByText(`Resetting the password for ${TEST_RESET_USER.email}`)).toBeVisible();
  const password = page.getByLabel(/^New password/);
  const confirm = page.getByLabel("Confirm new password");
  await expect(password).toHaveAttribute("autocomplete", "new-password");
  await expect(confirm).toHaveAttribute("autocomplete", "new-password");

  await password.fill(NEW_PASSWORD);
  await confirm.fill("not-the-same-password");
  await page.getByRole("button", { name: "Reset password" }).click();
  await expect(page.getByText("The passwords do not match.")).toBeVisible();

  // Django's password validators run through allauth.
  await password.fill("password");
  await confirm.fill("password");
  await page.getByRole("button", { name: "Reset password" }).click();
  await expect(page.getByText(/too common/i)).toBeVisible();

  await password.fill(NEW_PASSWORD);
  await confirm.fill(NEW_PASSWORD);
  await page.getByRole("button", { name: "Reset password" }).click();
  await expect(page.getByRole("status")).toContainText("Your password has been reset.");
  await expect(page.getByRole("status").getByRole("link", { name: "Log in" })).toHaveAttribute("href", "/account/login");
  await expect(page).toHaveURL(/\/account\/login$/, { timeout: 10_000 });

  // Every existing session ended with the old password.
  expect((await otherDevice.request.get(`${AUTH}/auth/session`)).status()).toBe(401);
  await otherDevice.close();

  await page.getByLabel("School email").fill(TEST_RESET_USER.email);
  await page.getByLabel("Password", { exact: true }).fill(NEW_PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).not.toHaveURL(/\/account\/login/);
  expect(await page.evaluate(async (url) => (await fetch(url)).status, `${AUTH}/auth/session`)).toBe(200);

  // The link only works once.
  await page.goto(resetPath);
  await expect(page.getByRole("alert").filter({ hasText: "This reset link has already been used." })).toBeVisible();
  await expect(page.getByRole("link", { name: "Request a new link" })).toHaveAttribute("href", "/account/forgot-password");
});

test("gives the same answer for an email without an account", async ({ page }) => {
  await page.goto("/account/forgot-password");
  await page.getByLabel("School email").fill("nobody-here@umd.edu");
  await page.getByRole("button", { name: "Send reset link" }).click();
  await expect(page.getByRole("status")).toContainText("If nobody-here@umd.edu belongs to a Tanu account");
});

test("explains expired and invalid reset links", async ({ page }) => {
  // A well-formed key stamped in 2001 (the token generator's epoch) is long expired.
  await page.goto("/account/password/reset/1-1-0123456789abcdef");
  await expect(page.getByRole("alert").filter({ hasText: "This reset link has expired." })).toBeVisible();

  await page.goto("/account/password/reset/not_a_real_key");
  await expect(page.getByRole("alert").filter({ hasText: "This reset link isn’t valid." })).toBeVisible();
  await page.getByRole("link", { name: "Return to login" }).click();
  await expect(page).toHaveURL(/\/account\/login$/);
});
