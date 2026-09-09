import { expect, test } from "@playwright/test";
import { authenticateContext, createDocument, createShareLink } from "./helpers";

test("a collaborator's text cursor is visible to the other person", async ({
  browser,
  baseURL,
}) => {
  const ownerCtx = await browser.newContext();
  const { displayName } = await authenticateContext(ownerCtx, baseURL!, "Sam Rivera");
  const doc = await createDocument(ownerCtx.request, baseURL!, "Presence");
  const link = await createShareLink(ownerCtx.request, baseURL!, doc.id, "editor");

  const ownerPage = await ownerCtx.newPage();
  await ownerPage.goto(`/d/${doc.slug}`);
  await ownerPage.locator(".cm-content").click();
  await ownerPage.keyboard.type("The owner is typing here");

  const guestPage = await browser.newPage();
  await guestPage.goto(`/s/${link.token}`);
  await guestPage.getByLabel("Your name").fill("Watcher");
  await guestPage.getByRole("button", { name: "Open document" }).click();
  await expect(guestPage.locator(".cm-content")).toContainText("The owner is typing", {
    timeout: 15_000,
  });

  // Owner moves the text caret; the guest sees a remote caret carrying the owner's name.
  await ownerPage.keyboard.press("Home");
  await ownerPage.keyboard.press("ArrowRight");

  await expect(guestPage.locator(".cm-ySelectionInfo").first()).toBeVisible({
    timeout: 15_000,
  });
  await expect(guestPage.locator(".cm-ySelectionInfo").first()).toContainText(
    displayName,
  );

  await ownerCtx.close();
});
