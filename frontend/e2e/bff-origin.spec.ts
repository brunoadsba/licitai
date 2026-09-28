import { test, expect } from "@playwright/test";

/** Fase 1 — BFF recusa escrita cross-origin (CSRF) e libera mesma origem. */
const live = process.env.E2E_LIVE === "1";

test.describe("BFF valida origem", () => {
  test.skip(!live, "Requer E2E_LIVE=1");

  test("POST com Origin externa retorna 403", async ({ request }) => {
    const res = await request.post("/api/proxy/documents", {
      headers: { Origin: "https://evil.example" },
      data: {},
    });
    expect(res.status()).toBe(403);
    expect(await res.json()).toEqual({ detail: "Origem não permitida." });
  });

  test("GET com Origin externa retorna 403", async ({ request }) => {
    const res = await request.get("/api/proxy/documents", {
      headers: { Origin: "https://evil.example" },
    });
    expect(res.status()).toBe(403);
  });

  test("mesma origem continua funcionando", async ({ page }) => {
    await page.goto("/");
    const res = await page.evaluate(() =>
      fetch("/api/proxy/documents").then((r) => r.status)
    );
    expect(res).not.toBe(403);
  });
});
