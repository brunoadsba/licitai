import { test, expect } from '@playwright/test';

/** P0.1 — página de confiança renderiza os 5 blocos com fonte. */
const live = process.env.E2E_LIVE === '1';

test.describe('Página Como confiamos', () => {
  test.skip(!live, 'Requer E2E_LIVE=1');

  test('/confianca tem 5 blocos com fonte', async ({ page }) => {
    await page.goto('/confianca');
    await expect(
      page.getByRole('heading', { name: 'Como confiamos' }),
    ).toBeVisible();
    for (const name of [
      'Precisão',
      'Recall em TR real',
      'Limites conhecidos',
      'Cobertura de testes',
      'Histórico de medição',
    ]) {
      await expect(page.getByRole('heading', { name })).toBeVisible();
    }
    await expect(page.getByText(/Fonte:/).first()).toBeVisible();
    await expect(page.getByText(/ainda não medido|Números desatualizados/)).toBeVisible();
  });
});
