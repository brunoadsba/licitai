import { test, expect } from "@playwright/test";

/**
 * Smoke de rotas estáticas (P0.1).
 * Requer E2E_LIVE=1 e frontend no ar.
 */
const live = process.env.E2E_LIVE === "1";

test.describe("P0.1 smoke routes", () => {
  test.skip(!live, "Requer E2E_LIVE=1");

  test("painel carrega", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Revisar Termos/i })).toBeVisible();
  });

  test("upload carrega", async ({ page }) => {
    await page.goto("/upload");
    await expect(page.getByRole("heading", { level: 1, name: "Enviar TR" })).toBeVisible();
    await expect(page.getByTestId("dropzone")).toBeVisible();
  });

  test("guia carrega", async ({ page }) => {
    await page.goto("/guia");
    await expect(page.getByRole("heading", { level: 1, name: "Guia do usuário" })).toBeVisible();
  });
});
