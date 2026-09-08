import { test, expect } from "@playwright/test";

/**
 * Smoke E2E.
 * - Sem E2E_LIVE=1: apenas placeholders (skip) — gate de estrutura.
 * - Com E2E_LIVE=1: espera backend/frontend reais (ou FakeLLM) e exercita fluxos.
 */
const live = process.env.E2E_LIVE === "1";

test.describe("smoke", () => {
  test("home carrega", async ({ page }) => {
    test.skip(!live && process.env.E2E_SKIP_HOME === "1", "home skip explícito");
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();
  });

  test("upload placeholder", async ({ page }) => {
    test.skip(!live, "Requer E2E_LIVE=1 (backend+FakeLLM)");
    await page.goto("/upload");
    await expect(page.getByText(/upload|enviar|documento/i).first()).toBeVisible();
  });

  test("analysis report placeholder", async ({ page }) => {
    test.skip(!live, "Requer E2E_LIVE=1 e analysis_id real");
    const analysisId = process.env.E2E_ANALYSIS_ID;
    test.skip(!analysisId, "Defina E2E_ANALYSIS_ID");
    await page.goto(`/report/${analysisId}`);
    await expect(page.locator("body")).toBeVisible();
  });

  test("gerar-tr placeholder", async ({ page }) => {
    test.skip(!live, "Requer E2E_LIVE=1");
    await page.goto("/gerar-tr");
    await expect(page.locator("body")).toBeVisible();
  });
});
