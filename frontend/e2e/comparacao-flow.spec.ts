import { test, expect } from "@playwright/test";

/** P2 — ferramentas avançadas (smoke + fluxos leves). */
const live = process.env.E2E_LIVE === "1";

test.describe("P2 advanced tools", () => {
  test.skip(!live, "Requer E2E_LIVE=1");

  test("comparacao abas", async ({ page }) => {
    await page.goto("/comparacao");
    await expect(page.getByRole("tab", { name: /Histórico/i })).toBeVisible();
    await page.getByRole("tab", { name: /Nova auditoria/i }).click();
    await page.getByRole("tab", { name: /Fornecedores/i }).click();
  });

  test("moldes novo molde visível", async ({ page }) => {
    await page.goto("/moldes");
    await expect(page.getByRole("button", { name: /Novo Molde/i })).toBeVisible();
  });

  test("versoes empty ou seletor", async ({ page }) => {
    await page.goto("/comparacao/versoes");
    await expect(
      page.getByRole("heading", { name: /Comparador de Versões/i }),
    ).toBeVisible();
  });

  test("gerar-tr wizard", async ({ page }) => {
    await page.goto("/gerar-tr");
    await expect(page.locator("body")).toBeVisible();
    await expect(page.getByText(/Dados|Contratação|Gerar|Requisitos/i).first()).toBeVisible();
  });
});
