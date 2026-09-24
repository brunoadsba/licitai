import path from "node:path";
import { test, expect } from "@playwright/test";

/** P0.4 — Proposta em Comparações não inicia análise de TR. */
const live = process.env.E2E_LIVE === "1";
const fixture = path.resolve(__dirname, "../../e2e/fixtures/sample-tr.docx");

test.describe("P0.4 upload proposta guard", () => {
  test.skip(!live, "Requer E2E_LIVE=1");
  test.setTimeout(180_000);

  test("proposta não chama start analysis", async ({ page, request }) => {
    const nome = `E2E UI Fornecedor ${Date.now()}`;
    const forn = await request.post("/api/proxy/fornecedores", {
      data: { nome, email: null, cnpj: null },
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
      await page.goto("/comparacao");
      await page.getByRole("tab", { name: "Fornecedores" }).click();
      await page.getByTestId("doc-classification").click();
      await page.getByRole("option", { name: /Público/i }).click();
      await page.getByLabel("Fornecedor da proposta").click();
      await page.getByRole("option", { name: nome, exact: true }).click();
      await page.getByLabel("Arquivo da proposta").setInputFiles(fixture);
      await page.getByTestId("proposta-upload-submit").click();
      await expect(page.getByTestId("proposta-upload-submit")).toBeEnabled({
        timeout: 120_000,
      });
      expect(startCalls, startCalls.join("\n")).toEqual([]);
    } finally {
      await request.delete(`/api/proxy/fornecedores/${fornecedorId}`);
    }
  });
});
