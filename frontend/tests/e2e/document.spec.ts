import { expect, test } from "@playwright/test";
import { authenticateContext } from "./helpers";

test("create a document, write Markdown, and reload — content persists", async ({
  page,
  context,
  baseURL,
}) => {
  await authenticateContext(context, baseURL!);

  await page.goto("/dashboard");
  await page.getByRole("button", { name: "New document" }).click();
  await expect(page).toHaveURL(/\/d\/.+/);

  const source = page.locator(".cm-content");
  await source.click();
  await page.keyboard.type("# Release notes\n\nShipped the **split editor**.");

  // The preview pane renders it.
  const preview = page.locator(".comark-prose");
  await expect(preview.getByRole("heading", { name: "Release notes" })).toBeVisible();
  await expect(preview).toContainText("Shipped the split editor.");

  // Give the debounced markdown cache + Yjs persistence a moment, then reload.
  await page.waitForTimeout(2500);
  await page.reload();

  await expect(page.locator(".cm-content")).toContainText("# Release notes");
  await expect(page.locator(".comark-prose")).toContainText("Shipped the split editor.");
});
