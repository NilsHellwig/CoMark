import { test } from "@playwright/test";
import { authenticateContext, createDocument, createShareLink } from "./helpers";

const SHOT_DIR = "../docs";
const viewport = { width: 1440, height: 900 };

const SAMPLE = `# Q3 product roadmap

Collaborative editing is our focus this quarter.

## Shipping now

- **Live cursors** — see where everyone is typing
- Share links for people **with or without an account**
- One-click Markdown export

## In review

> The split view keeps the raw Markdown honest while the
> preview stays a keystroke behind.

\`\`\`ts
const status = await comark.health();
\`\`\`
`;

test.describe("README screenshots", () => {
  test("landing + dashboard", async ({ browser, baseURL }) => {
    const ctx = await browser.newContext({ viewport, deviceScaleFactor: 2 });
    const page = await ctx.newPage();

    await page.goto("/");
    await page.waitForTimeout(400);
    await page.screenshot({ path: `${SHOT_DIR}/landing.png` });

    await authenticateContext(ctx, baseURL!, "Maya Chen");
    await createDocument(ctx.request, baseURL!, "Q3 product roadmap");
    await createDocument(ctx.request, baseURL!, "Design system tokens");
    await createDocument(ctx.request, baseURL!, "Onboarding checklist");
    await page.goto("/dashboard");
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SHOT_DIR}/dashboard.png` });

    await ctx.close();
  });

  test("split editor with a remote cursor", async ({ browser, baseURL }) => {
    const ownerCtx = await browser.newContext({ viewport, deviceScaleFactor: 2 });
    await authenticateContext(ownerCtx, baseURL!, "Maya Chen");
    const doc = await createDocument(ownerCtx.request, baseURL!, "Q3 product roadmap");
    const link = await createShareLink(ownerCtx.request, baseURL!, doc.id, "editor");

    const ownerPage = await ownerCtx.newPage();
    await ownerPage.goto(`/d/${doc.slug}`);
    await ownerPage.locator(".cm-content").click();
    await ownerPage.keyboard.insertText(SAMPLE);

    const guestCtx = await browser.newContext({ viewport });
    const guestPage = await guestCtx.newPage();
    await guestPage.goto(`/s/${link.token}`);
    await guestPage.getByLabel("Your name").fill("Priya");
    await guestPage.getByRole("button", { name: "Open document" }).click();
    await guestPage.locator(".cm-content").waitFor();
    await guestPage.waitForTimeout(800);

    // Guest places their caret mid-document so the owner's screenshot shows it.
    await guestPage.locator(".cm-content").click();
    await guestPage.keyboard.press("Control+Home");
    for (let i = 0; i < 6; i += 1) await guestPage.keyboard.press("ArrowDown");
    await guestPage.keyboard.press("End");
    await ownerPage.waitForTimeout(700);

    await ownerPage.screenshot({ path: `${SHOT_DIR}/editor.png` });

    await ownerCtx.close();
    await guestCtx.close();
  });
});
