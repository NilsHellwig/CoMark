import { expect, test } from "@playwright/test";
import { authenticateContext, createDocument, createShareLink } from "./helpers";

test("two people edit the same document live via a share link", async ({
  browser,
  baseURL,
}) => {
  const ownerCtx = await browser.newContext();
  await authenticateContext(ownerCtx, baseURL!);
  const doc = await createDocument(ownerCtx.request, baseURL!, "Live collab");
  const link = await createShareLink(ownerCtx.request, baseURL!, doc.id, "editor");

  const ownerPage = await ownerCtx.newPage();
  await ownerPage.goto(`/d/${doc.slug}`);
  await ownerPage.locator(".cm-content").click();
  await ownerPage.keyboard.type("Line from the owner. ");

  // Guest joins through the share link.
  const guestCtx = await browser.newContext();
  const guestPage = await guestCtx.newPage();
  await guestPage.goto(`/s/${link.token}`);
  await guestPage.getByLabel("Your name").fill("Guest Robin");
  await guestPage.getByRole("button", { name: "Open document" }).click();
  await expect(guestPage).toHaveURL(/\/d\/.+/);

  // Guest sees the owner's text, then adds their own.
  await expect(guestPage.locator(".cm-content")).toContainText("Line from the owner.", {
    timeout: 15_000,
  });
  await guestPage.locator(".cm-content").click();
  await guestPage.keyboard.press("End");
  await guestPage.keyboard.type("And a line from the guest.");

  // Owner sees the guest's contribution — in the source and the preview.
  await expect(ownerPage.locator(".cm-content")).toContainText(
    "And a line from the guest.",
    { timeout: 15_000 },
  );
  await expect(ownerPage.locator(".comark-prose")).toContainText(
    "And a line from the guest.",
  );

  await ownerCtx.close();
  await guestCtx.close();
});
