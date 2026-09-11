import { test, expect } from "@playwright/test";

/** P1 — relatório e filas. */
const live = process.env.E2E_LIVE === "1";
const analysisId = process.env.E2E_ANALYSIS_ID;
const documentId = process.env.E2E_DOCUMENT_ID;

test.describe("P1 report and queues", () => {
  test.skip(!live, "Requer E2E_LIVE=1");

  test("report carrega com analysis id", async ({ page }) => {
    test.skip(!analysisId, "Defina E2E_ANALYSIS_ID");
    await page.goto(`/report/${analysisId}`);
    await expect(page.locator("body")).toBeVisible();
    await expect(page.getByText(/Parecer|Relatório|Partes obrigatórias|Prioridade/i).first()).toBeVisible({
      timeout: 30_000,
    });
  });

  test("filas Revisar agora / Ver todas", async ({ page }) => {
    test.skip(!documentId, "Defina E2E_DOCUMENT_ID");
    await page.goto(`/analysis/${documentId}`);
    await expect(page.getByTestId("queue-priority")).toBeVisible({ timeout: 60_000 });
    await page.getByTestId("queue-all").click();
    await page.getByTestId("queue-priority").click();
  });
});
