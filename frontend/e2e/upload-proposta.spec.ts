import path from "node:path";
import { test, expect } from "@playwright/test";

/** P0.4 — Proposta não inicia análise de TR. */
const live = process.env.E2E_LIVE === "1";
const fixture = path.resolve(__dirname, "../../e2e/fixtures/sample-tr.docx");

test.describe("P0.4 upload proposta guard", () => {
  test.skip(!live, "Requer E2E_LIVE=1");
  test.setTimeout(180_000);

  test("proposta não chama start analysis", async ({ page, request }) => {
    const forn = await request.post("/api/proxy/fornecedores", {
      data: { nome: "E2E UI Fornecedor", email: null, cnpj: null },
    });
    expect(forn.ok()).toBeTruthy();
    const { id: fornecedorId } = await forn.json();

    const startCalls: string[] = [];
    page.on("request", (req) => {
      if (req.method() === "POST" && /\/analysis\/.+\/start/.test(req.url())) {
        startCalls.push(req.url());
      }
    });

    try {
      await page.goto("/upload");
      await page.getByTestId("options-advanced-toggle").click();
      await page.getByTestId("doc-type").click();
      await page.getByRole("option", { name: "Proposta de fornecedor" }).click();
      await page.getByLabel("Fornecedor da proposta").click();
      await page.getByRole("option", { name: "E2E UI Fornecedor" }).click();

      await page.locator('input[type="file"]').setInputFiles(fixture);
      await page.getByTestId("upload-submit").click();

      await expect(page.getByText(/Proposta enviada/i)).toBeVisible({ timeout: 120_000 });
      await page.waitForURL(/\/comparacao/, { timeout: 30_000 });
      expect(startCalls, startCalls.join("\n")).toEqual([]);
    } finally {
      await request.delete(`/api/proxy/fornecedores/${fornecedorId}`);
    }
  });
});
