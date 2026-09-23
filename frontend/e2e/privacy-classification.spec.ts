import path from "node:path";
import { test, expect } from "@playwright/test";

/** P0 privacidade — seletor obrigatório após a Fase 0A. */
const live = process.env.E2E_LIVE === "1";
const fixture = path.resolve(__dirname, "../../e2e/fixtures/sample-tr.docx");

test.describe("P0 classificação fail-closed", () => {
  test.skip(!live, "Requer E2E_LIVE=1");

  test("upload exige classificação antes de enviar", async ({ page }) => {
    await page.goto("/upload");
    await expect(page.getByTestId("doc-classification")).toBeVisible();

    await page.locator('input[type="file"]').setInputFiles(fixture);
    await expect(page.getByTestId("upload-submit")).toBeVisible();
    await page.getByTestId("upload-submit").click();

    await expect(page.getByText(/Selecione a classificação do documento/i)).toBeVisible();
    await expect(page).toHaveURL(/\/upload/);
  });

  test("gerar-tr exige classificação para avançar", async ({ page }) => {
    await page.goto("/gerar-tr");
    await expect(page.locator("#tr-classificacao")).toBeVisible();

    await page.locator("#tr-objeto").fill(
      "Contratação de empresa especializada em manutenção preventiva de ar condicionado.",
    );
    await page.locator("#tr-justificativa").fill(
      "A contratação é necessária para manter a infraestrutura operacional da autoridade portuária.",
    );
    await page.getByRole("button", { name: /Avançar para Passo 2/i }).click();

    await expect(page.getByText(/Selecione a classificação do termo/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /Avançar para Passo 2/i })).toBeVisible();
  });
});
