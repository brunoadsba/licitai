document.addEventListener('DOMContentLoaded', async () => {
  const listContainer = document.getElementById('documents-list');
  const statusDiv = document.getElementById('status');

  try {
    const response = await fetch('http://localhost:8000/api/v1/documents');
    if (!response.ok) throw new Error('Servidor LicitAI não acessível na porta 8000.');

    const data = await response.json();
    const trDocs = (data.documents || []).filter((d) => d.document_type === 'tr');

    if (trDocs.length === 0) {
      listContainer.innerHTML = '<div style="font-size:11px; color:#94a3b8; text-align:center;">Nenhum TR encontrado. Gere um novo no LicitAI.</div>';
      return;
    }

    listContainer.innerHTML = '';

    trDocs.slice(0, 5).forEach((doc) => {
      const card = document.createElement('div');
      card.className = 'card';
      card.innerHTML = `
        <div class="card-title">${doc.filename_original}</div>
        <div class="card-meta">${doc.total_items} itens — ${new Date(doc.created_at).toLocaleDateString('pt-BR')}</div>
      `;

      card.addEventListener('click', async () => {
        statusDiv.innerText = 'Buscando conteúdo do TR...';

        try {
          const detailRes = await fetch(`http://localhost:8000/api/v1/documents/${doc.id}`);
          const detailData = await detailRes.json();

          let htmlParts = [`<h1>${detailData.filename_original.toUpperCase()}</h1>\n`];
          (detailData.items || []).forEach((item) => {
            htmlParts.push(`<h2>${item.item_number} ${item.title || ''}</h2>\n<p>${(item.content || '').replace(/\n/g, '<br/>')}</p>\n`);
          });

          const fullHtml = htmlParts.join('');

          // Enviar para o content script da aba ativa no SEI
          const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
          if (tab) {
            chrome.tabs.sendMessage(tab.id, { action: 'INJECT_TR', html: fullHtml }, (resp) => {
              if (chrome.runtime.lastError) {
                statusDiv.innerText = 'Abra a aba do SEI e clique novamente.';
              } else {
                statusDiv.innerText = 'TR injetado com sucesso!';
              }
            });
          }
        } catch (e) {
          statusDiv.innerText = 'Erro ao buscar itens do TR.';
        }
      });

      listContainer.appendChild(card);
    });
  } catch (err) {
    listContainer.innerHTML = `<div style="font-size:11px; color:#f87171; text-align:center;">Erro: ${err.message}</div>`;
  }
});
