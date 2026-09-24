document.addEventListener('DOMContentLoaded', async () => {
  const listContainer = document.getElementById('documents-list');
  const statusDiv = document.getElementById('status');
  const BFF = 'http://127.0.0.1:3000/api/proxy';
  const escapeText = (window.LicitAISanitize || { escapeText: String }).escapeText;
  const sanitizeHtml = (window.LicitAISanitize || { sanitizeHtml: (s) => s }).sanitizeHtml;

  function showError(message) {
    listContainer.replaceChildren();
    const el = document.createElement('div');
    el.style.cssText = 'font-size:11px;color:#f87171;text-align:center;';
    el.textContent = message;
    listContainer.appendChild(el);
  }

  try {
    const response = await fetch(`${BFF}/documents`);
    if (!response.ok) {
      throw new Error('Abra o LicitAI em http://127.0.0.1:3000 (BFF).');
    }

    const data = await response.json();
    const trDocs = (data.documents || []).filter((d) => d.document_type === 'tr');

    if (trDocs.length === 0) {
      listContainer.replaceChildren();
      const empty = document.createElement('div');
      empty.style.cssText = 'font-size:11px;color:#94a3b8;text-align:center;';
      empty.textContent = 'Nenhum TR encontrado. Gere ou analise um no LicitAI.';
      listContainer.appendChild(empty);
      return;
    }

    listContainer.replaceChildren();

    trDocs.slice(0, 5).forEach((doc) => {
      const card = document.createElement('div');
      card.className = 'card';

      const title = document.createElement('div');
      title.className = 'card-title';
      title.textContent = doc.filename_original || 'TR';

      const meta = document.createElement('div');
      meta.className = 'card-meta';
      meta.textContent = `${doc.total_items || 0} itens`;

      const hint = document.createElement('div');
      hint.className = 'card-meta';
      hint.style.marginTop = '4px';
      hint.style.color = '#2AAFA0';
      hint.textContent = 'Usa TR corrigido (corrected-html) quando existir';

      card.appendChild(title);
      card.appendChild(meta);
      card.appendChild(hint);

      card.addEventListener('click', async () => {
        statusDiv.textContent = 'Buscando TR corrigido…';
        try {
          const analysesRes = await fetch(`${BFF}/analysis/document/${doc.id}`);
          const analyses = await analysesRes.json();
          const completed = (analyses || []).find((a) =>
            ['completed', 'completed_with_errors'].includes(a.status),
          );

          let fullHtml = '';
          if (completed) {
            const corrRes = await fetch(`${BFF}/analysis/${completed.id}/corrected-html`);
            if (corrRes.ok) {
              const corrData = await corrRes.json();
              fullHtml = sanitizeHtml(corrData.html || '');
              statusDiv.textContent = 'Injetando TR corrigido (pós-revisão)…';
            }
          }

          if (!fullHtml) {
            statusDiv.textContent = 'Sem correções aprovadas — usando texto original…';
            const detailRes = await fetch(`${BFF}/documents/${doc.id}`);
            const detailData = await detailRes.json();
            const parts = [`<h1>${escapeText((detailData.filename_original || 'TR').toUpperCase())}</h1>`];
            (detailData.items || []).forEach((item) => {
              const heading = `${escapeText(item.item_number || '')} ${escapeText(item.title || '')}`.trim();
              const body = escapeText(item.content || '').replace(/\n/g, '<br>');
              parts.push(`<h2>${heading}</h2><p>${body}</p>`);
            });
            fullHtml = sanitizeHtml(parts.join(''));
          }

          const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
          if (tab) {
            chrome.tabs.sendMessage(tab.id, { action: 'INJECT_TR', html: fullHtml }, () => {
              if (chrome.runtime.lastError) {
                statusDiv.textContent = 'Abra a aba do SEI e clique novamente.';
              } else {
                statusDiv.textContent = 'TR sanitizado enviado ao editor.';
              }
            });
          }
        } catch (e) {
          statusDiv.textContent = 'Erro ao buscar conteúdo do TR.';
        }
      });

      listContainer.appendChild(card);
    });
  } catch (err) {
    showError(err.message || 'Falha ao falar com o LicitAI.');
  }
});
