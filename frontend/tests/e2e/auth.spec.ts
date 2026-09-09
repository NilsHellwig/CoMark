import { expect, test } from "@playwright/test";
import { uniqueEmail } from "./helpers";

test("register, stay signed in across reload, then sign out", async ({ page }) => {
  const email = uniqueEmail();

  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("supersecret123");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Documents" })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("heading", { name: "Documents" })).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);

  // Protected route bounces back to login.
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login/);
});
