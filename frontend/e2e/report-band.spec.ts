import { test, expect } from '@playwright/test';

/** 0.2 — relatório parcial mostra faixa calibrada colada ao número. */
const live = process.env.E2E_LIVE === '1';
// Análise real parcial: 186/257, completed_with_errors.
const PARTIAL_ID = 'f9648727-ce6e-4a64-8b8e-78770b39e84a';

test.describe('Relatório calibrado', () => {
  test.skip(!live, 'Requer E2E_LIVE=1');

  test('/report parcial tem faixa + cobertura no número', async ({ page }) => {
    await page.goto(`/report/${PARTIAL_ID}`);
    await expect(page.getByText(/Análise parcial: 186 de 257 itens/)).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByText(/Entenda os limites/)).toBeVisible();
  });
});
