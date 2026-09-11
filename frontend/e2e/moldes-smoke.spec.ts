import { test, expect } from "@playwright/test";

/** P2 — smoke Moldes (arquivo dedicado). */
const live = process.env.E2E_LIVE === "1";

test.describe("P2 moldes smoke", () => {
  test.skip(!live, "Requer E2E_LIVE=1");

  test("página moldes", async ({ page }) => {
    await page.goto("/moldes");
    await expect(page.getByRole("heading", { level: 1, name: /Moldes/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Novo Molde/i })).toBeVisible();
  });
});
