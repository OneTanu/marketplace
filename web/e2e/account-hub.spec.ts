import { randomUUID } from "node:crypto";

import { expect, test } from "@playwright/test";

import { signIn } from "./sign-in";
import { TEST_BUYER, TEST_MODERATOR } from "./test-user";

const PHONE = { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true };

test.describe("on a phone", () => {
  test.use(PHONE);

  test("Profile is the account hub, with links to the public profile", async ({ context, page, baseURL }) => {
    await signIn(context, baseURL!, TEST_BUYER);
    await page.goto("/profile");
    const account = page.getByRole("navigation", { name: "Account" });
    await expect(account.getByRole("listitem")).toHaveText(["My listings", "Saved", "Saved searches", "Meetup preferences", "Account status", "Log out"]);
    // The Selling, Sold and Bookmarks tabs are gone.
    await expect(page.getByRole("tab")).toHaveCount(0);
    await expect(page.getByText(/^\d+ followers?$/)).toBeVisible();

    await expect(page.getByRole("link", { name: "View profile" })).toHaveAttribute("href", `/users/${TEST_BUYER.username}`);
    // Tapping the card opens the public profile too.
    await page.getByRole("heading", { level: 1 }).click();
    await expect(page).toHaveURL(`/users/${TEST_BUYER.username}`);
    await expect(page.getByText("This is how other students see your profile.")).toBeVisible();

    await page.goBack();
    await account.getByRole("link", { name: "Saved", exact: true }).click();
    await expect(page).toHaveURL("/profile/saved");
    await expect(page.getByRole("heading", { level: 1, name: "Saved" })).toBeVisible();
  });

  test("Edit profile is a focused screen, and the change shows on the public profile", async ({ context, page, baseURL }) => {
    await signIn(context, baseURL!, TEST_BUYER);
    await page.goto("/profile");
    await page.getByRole("link", { name: "Edit profile" }).click();
    await expect(page).toHaveURL("/profile/edit");
    await expect(page.getByRole("heading", { level: 1, name: "Edit profile" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Back to profile" })).toHaveAttribute("href", "/profile");
    await expect(page.getByRole("searchbox", { name: "Search listings" })).toBeHidden();
    await expect(page.getByRole("contentinfo")).toHaveCount(0);

    const description = `Selling dorm stuff ${randomUUID().slice(0, 8)}`;
    await page.getByLabel(/^Description/).fill(description);
    await page.getByRole("button", { name: "Save profile" }).click();
    await expect(page.getByRole("status")).toContainText("Profile saved.");
    await page.getByRole("status").getByRole("link", { name: "View profile" }).click();
    await expect(page.getByText(description)).toBeVisible();
  });
});

test("staff get a Moderation row", async ({ context, page, baseURL }) => {
  await signIn(context, baseURL!, TEST_MODERATOR);
  await page.goto("/profile");
  await expect(page.getByRole("navigation", { name: "Account" }).getByRole("link", { name: "Moderation" })).toHaveAttribute("href", "/moderation");
});

test.describe("the footer", () => {
  test.use(PHONE);

  test("shows on Terms, Privacy, Profile and the account pages only, at 13px or larger", async ({ browser, page, baseURL }) => {
    for (const path of ["/terms", "/privacy", "/account/login", "/account/signup"]) {
      await page.goto(path);
      const disclaimer = page.getByRole("contentinfo").getByText("Independent and not affiliated with or endorsed by any university.");
      await expect(disclaimer, path).toBeVisible();
      expect(await disclaimer.evaluate((el) => parseFloat(getComputedStyle(el).fontSize)), path).toBeGreaterThanOrEqual(13);
    }

    const student = await browser.newContext({ baseURL, ...PHONE });
    await signIn(student, baseURL!, TEST_BUYER);
    const studentPage = await student.newPage();
    await studentPage.goto("/profile");
    await expect(studentPage.getByRole("contentinfo")).toBeVisible();
    for (const path of ["/", "/search", "/deals", "/profile/saved"]) {
      await studentPage.goto(path);
      await expect(studentPage.getByRole("heading", { level: 1 }).first(), path).toBeVisible();
      await expect(studentPage.getByRole("contentinfo"), path).toHaveCount(0);
      // Without a footer, the page still ends above the bottom bar.
      await studentPage.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      // The lowest visible piece of content on the page (spacers are aria-hidden and empty).
      const contentBottom = await studentPage.locator("body > main").evaluate((main) => Math.max(...[...main.querySelectorAll("*")]
        .filter((el) => el.children.length === 0 && !el.closest("[aria-hidden=true]") && el.getBoundingClientRect().height > 0)
        .map((el) => el.getBoundingClientRect().bottom)));
      const barTop = await studentPage.getByRole("navigation", { name: "Main" }).evaluate((el) => el.getBoundingClientRect().top);
      expect(contentBottom, path).toBeLessThanOrEqual(barTop + 1);
    }
    await student.close();
  });
});
