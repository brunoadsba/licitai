document.addEventListener('DOMContentLoaded', async () => {
  const listContainer = document.getElementById('documents-list');
  const statusDiv = document.getElementById('status');
  const API = 'http://localhost:8000';

  try {
    const response = await fetch(`${API}/api/v1/documents/`);
    if (!response.ok) throw new Error('Servidor LicitAI não acessível na porta 8000.');

    const data = await response.json();
    const trDocs = (data.documents || []).filter((d) => d.document_type === 'tr');

    if (trDocs.length === 0) {
      listContainer.innerHTML =
        '<div style="font-size:11px; color:#94a3b8; text-align:center;">Nenhum TR encontrado. Gere ou analise um no LicitAI.</div>';
      return;
    }

    listContainer.innerHTML = '';

    trDocs.slice(0, 5).forEach((doc) => {
      const card = document.createElement('div');
      card.className = 'card';
      card.innerHTML = `
        <div class="card-title">${doc.filename_original}</div>
        <div class="card-meta">${doc.total_items} itens — ${new Date(doc.created_at).toLocaleDateString('pt-BR')}</div>
        <div class="card-meta" style="margin-top:4px;color:#2AAFA0;">Prefere TR corrigido (pós-revisão) quando existir</div>
      `;

      card.addEventListener('click', async () => {
        statusDiv.innerText = 'Buscando TR corrigido…';

        try {
          const analysesRes = await fetch(`${API}/api/v1/analysis/document/${doc.id}`);
          const analyses = await analysesRes.json();
          const completed = (analyses || []).find((a) =>
            ['completed', 'completed_with_errors'].includes(a.status),
          );

          let fullHtml = '';

          if (completed) {
            try {
              const corrRes = await fetch(
                `${API}/api/v1/analysis/${completed.id}/corrected-html`,
              );
              if (corrRes.ok) {
                const corrData = await corrRes.json();
                fullHtml = corrData.html;
                statusDiv.innerText = 'Injetando TR corrigido (pós-revisão)…';
              }
            } catch (_) {
              /* fallback abaixo */
            }
          }

          if (!fullHtml) {
            statusDiv.innerText = 'Sem correções aprovadas — usando texto original…';
            const detailRes = await fetch(`${API}/api/v1/documents/${doc.id}`);
            const detailData = await detailRes.json();
            const htmlParts = [`<h1>${detailData.filename_original.toUpperCase()}</h1>\n`];
            (detailData.items || []).forEach((item) => {
              htmlParts.push(
                `<h2>${item.item_number} ${item.title || ''}</h2>\n<p>${(item.content || '').replace(/\n/g, '<br/>')}</p>\n`,
              );
            });
            fullHtml = htmlParts.join('');
          }

          const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
          if (tab) {
            chrome.tabs.sendMessage(tab.id, { action: 'INJECT_TR', html: fullHtml }, () => {
              if (chrome.runtime.lastError) {
                statusDiv.innerText = 'Abra a aba do SEI e clique novamente.';
              } else {
                statusDiv.innerText = 'TR injetado com sucesso!';
              }
            });
          }
        } catch (e) {
          statusDiv.innerText = 'Erro ao buscar conteúdo do TR.';
        }
      });

      listContainer.appendChild(card);
    });
  } catch (err) {
    listContainer.innerHTML = `<div style="font-size:11px; color:#f87171; text-align:center;">Erro: ${err.message}</div>`;
  }
});
