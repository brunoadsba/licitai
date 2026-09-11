import { test, expect } from "@playwright/test";

/** P0.5 / P0.6 — Review SEI + Art.6 (precisa E2E_DOCUMENT_ID = document_id). */
const live = process.env.E2E_LIVE === "1";
const documentId = process.env.E2E_DOCUMENT_ID;

test.describe("P0.5–P0.6 analysis review SEI Art6", () => {
  test.skip(!live, "Requer E2E_LIVE=1");
  test.skip(!documentId, "Defina E2E_DOCUMENT_ID (document_id com análise completed)");

  test("Art.6 panel e gate SEI", async ({ page }) => {
    await page.goto(`/analysis/${documentId}`);

    const art6 = page.getByTestId("art6-panel");
    // Pode não renderizar se checklist vazio
    if (await art6.count()) {
      await expect(art6).toContainText(/Partes obrigatórias do TR/i);
    }

    const sei = page.getByTestId("sei-pack-btn");
    await expect(sei).toBeVisible({ timeout: 60_000 });

    const approve = page.getByTestId("review-approve").first();
    if ((await approve.count()) === 0) {
      test.skip(true, "Sem correções para aprovar nesta análise");
    }

    const wasDisabled = await sei.isDisabled();
    await approve.click();
    await expect(page.getByText(/aprovada|cópia SEI liberada/i)).toBeVisible({ timeout: 15_000 });

    if (wasDisabled) {
      await expect(sei).toBeEnabled({ timeout: 10_000 });
    }
  });
});
