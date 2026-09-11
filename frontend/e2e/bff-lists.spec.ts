import { test, expect } from "@playwright/test";

/** P0.2 — BFF lists sem banner de erro de proxy. */
const live = process.env.E2E_LIVE === "1";

test.describe("P0.2 BFF list pages", () => {
  test.skip(!live, "Requer E2E_LIVE=1");

  for (const { path, heading } of [
    { path: "/comparacao", heading: /Auditoria TR/i },
    { path: "/comparacao/versoes", heading: /Comparador de Versões/i },
    { path: "/moldes", heading: /Moldes de Regras/i },
  ]) {
    test(`${path} sem erro de proxy`, async ({ page }) => {
      const proxyFails: string[] = [];
      page.on("response", (res) => {
        const url = res.url();
        if (url.includes("/api/proxy/") && (res.status() === 404 || res.status() >= 500)) {
          proxyFails.push(`${res.status()} ${url}`);
        }
      });

      await page.goto(path);
      await expect(page.getByRole("heading", { name: heading }).first()).toBeVisible();
      await expect(page.getByText(/Não foi possível carregar/i)).toHaveCount(0);
      await expect(page.getByText(/backend está rodando/i)).toHaveCount(0);
      expect(proxyFails, proxyFails.join("\n")).toEqual([]);
    });
  }
});
