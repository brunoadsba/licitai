import path from "node:path";
import { test, expect } from "@playwright/test";

/** P0.3 — Upload TR happy path (pode demorar: parse + start). */
const live = process.env.E2E_LIVE === "1";
const fixture = path.resolve(__dirname, "../../e2e/fixtures/sample-tr.docx");

test.describe("P0.3 upload TR", () => {
  test.skip(!live, "Requer E2E_LIVE=1 + worker");
  test.setTimeout(300_000);

  test("envia TR e abre análise", async ({ page }) => {
    await page.goto("/upload");
    await expect(page.getByTestId("dropzone")).toBeVisible();

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(fixture);
    await expect(page.getByTestId("upload-submit")).toBeVisible();
    await page.getByTestId("upload-submit").click();

    await page.waitForURL(/\/analysis\/[0-9a-f-]{36}/i, { timeout: 240_000 });
    await expect(page.getByTestId("sei-pack-btn").or(page.getByText(/Análise em andamento|Revisar agora/i))).toBeVisible({
      timeout: 60_000,
    });
  });
});
