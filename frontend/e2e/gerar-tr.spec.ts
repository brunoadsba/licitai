import { test, expect } from "@playwright/test";

/** P2 — Gerar TR smoke. */
const live = process.env.E2E_LIVE === "1";

test.describe("P2 gerar-tr", () => {
  test.skip(!live, "Requer E2E_LIVE=1");

  test("wizard carrega", async ({ page }) => {
    await page.goto("/gerar-tr");
    await expect(page.locator("body")).toBeVisible();
    await expect(page.getByText(/Dados|Contratação|Gerar|Requisitos/i).first()).toBeVisible();
  });
});
