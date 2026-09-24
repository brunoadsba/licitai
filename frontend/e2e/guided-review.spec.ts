import { test, expect } from '@playwright/test';

const live = process.env.E2E_LIVE === '1';
const documentId = process.env.E2E_DOCUMENT_ID || '';

test.describe('Guiado + sugestão do revisor', () => {
  test.skip(!live, 'Requer E2E_LIVE=1');
  test.skip(!documentId, 'Defina E2E_DOCUMENT_ID');

  test('guided-review mostra sugestão e aceitação', async ({ page }) => {
    await page.goto(`/analysis/${documentId}`);

    const guided = page.getByTestId('guided-review');
    await expect(guided).toBeVisible({ timeout: 30_000 });
    const guidedBtn = page.getByTestId('queue-priority');
    await expect(guidedBtn).toBeVisible();

    const suggestion = page.getByTestId('review-suggestion');
    if ((await suggestion.count()) > 0) {
      await expect(suggestion).toContainText(/Sugestão:/);
      const accept = page.getByTestId('accept-suggestion');
      if (await accept.isVisible()) {
        await accept.click();
        await expect(page.getByText(/aprovada|rejeitada|ajustada/i)).toBeVisible({ timeout: 15_000 });
      }
    }

    const cardSug = page.getByTestId('card-suggestion').first();
    if (await cardSug.count()) {
      await expect(cardSug).toContainText(/Sugestão:/);
    }
  });
});
