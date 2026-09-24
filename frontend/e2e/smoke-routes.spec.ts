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
    await expect(page.getByRole("heading", { name: /Seus TRs/i })).toBeVisible();
  });

  test("upload carrega", async ({ page }) => {
    await page.goto("/upload");
    await expect(page.getByRole("heading", { level: 1, name: "Enviar TR" })).toBeVisible();
    await expect(page.getByTestId("dropzone")).toBeVisible();
    await expect(page.getByTestId("doc-classification")).toBeVisible();
  });

  test("guia carrega", async ({ page }) => {
    await page.goto("/guia");
    await expect(page.getByRole("heading", { level: 1, name: "Como usar" })).toBeVisible();
  });

  test("complementos carrega", async ({ page }) => {
    await page.goto("/complementos");
    await expect(
      page.getByRole("heading", { level: 1, name: "Complementos" }),
    ).toBeVisible();
    await expect(page.getByRole("link", { name: "Gerar TR" })).toBeVisible();
    const trailHome = page.getByRole("navigation", { name: "Trilha de navegação" });
    await expect(trailHome.getByRole("link", { name: "Painel" })).toBeVisible();
    await expect(trailHome.getByText("Complementos")).toBeVisible();
    await page.getByRole("link", { name: "Gerar TR" }).click();
    const trail = page.getByRole("navigation", { name: "Trilha de navegação" });
    await expect(trail.getByRole("link", { name: "Complementos" })).toBeVisible();
    await expect(trail.getByText("Gerar TR")).toBeVisible();
  });
});
