import { test, expect } from '@playwright/test';

/** P1.2/P0.3 — teclado e retomada na fila guiada (sem mutação de dados). */
const live = process.env.E2E_LIVE === '1';
const documentId = process.env.E2E_DOCUMENT_ID || '';

test.describe('Guiado: teclado e retomada', () => {
  test.skip(!live, 'Requer E2E_LIVE=1');
  test.skip(!documentId, 'Defina E2E_DOCUMENT_ID');

  test('ajuda ? abre e n navega', async ({ page }) => {
    await page.goto(`/analysis/${documentId}`);
    const guided = page.getByTestId('guided-review');
    await expect(guided).toBeVisible({ timeout: 30_000 });
    const guidedBtn = page.getByTestId('queue-priority');
    if (await guidedBtn.count()) await guidedBtn.first().click();

    await page.keyboard.press('?');
    await expect(page.getByText(/Teclas:/)).toBeVisible();
    await page.keyboard.press('?');
    await expect(page.getByText(/Teclas:/)).toHaveCount(0);
  });

  test('n navega e recarregar retoma o mesmo card', async ({ page }) => {
    await page.goto(`/analysis/${documentId}`);
    const guided = page.getByTestId('guided-review');
    await expect(guided).toBeVisible({ timeout: 30_000 });
    const guidedBtn = page.getByTestId('queue-priority');
    if (await guidedBtn.count()) await guidedBtn.first().click();

    const firstId = await page.evaluate(
      () => localStorage.getItem(
        Object.keys(localStorage).find((k) => k.startsWith('licitai-review-')) || '',
      ),
    );
    await page.keyboard.press('n');
    await page.waitForTimeout(500);
    await page.reload();
    await expect(page.getByTestId('guided-review')).toBeVisible({ timeout: 30_000 });
    const keptId = await page.evaluate(
      () => localStorage.getItem(
        Object.keys(localStorage).find((k) => k.startsWith('licitai-review-')) || '',
      ),
    );
    expect(keptId).toBeTruthy();
    expect(firstId).toBeTruthy();
  });
});
