/**
 * Script de Conteúdo da Extensão LicitAI para o SEI.
 * Detecta o editor de texto do SEI e injeta o HTML do TR gerado ou corrigido.
 */

(function () {
  'use strict';

  console.log('[LicitAI] Extensão carregada no SEI.');

  // Injetar painel flutuante discreto no canto inferior direito
  function criarPainelFlutuante() {
    if (document.getElementById('licitai-floating-panel')) return;

    const panel = document.createElement('div');
    panel.id = 'licitai-floating-panel';
    panel.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 999999;
      background: #0f172a;
      color: #ffffff;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 12px 16px;
      font-family: system-ui, -apple-system, sans-serif;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      gap: 10px;
    `;

    panel.innerHTML = `
      <span style="font-size: 18px;">🪄</span>
      <div>
        <div style="font-size: 12px; font-weight: bold;">LicitAI no SEI</div>
        <div style="font-size: 10px; color: #94a3b8;">Clique no ícone da extensão para injetar TR</div>
      </div>
      <button id="licitai-btn-close" style="background:none; border:none; color:#94a3b8; cursor:pointer; font-weight:bold; margin-left:8px;">✕</button>
    `;

    document.body.appendChild(panel);

    document.getElementById('licitai-btn-close').addEventListener('click', () => {
      panel.style.display = 'none';
    });
  }

  // Tentar encontrar o editor do SEI (CKEditor, TinyMCE ou iFrame)
  function injetarHtmlNoSEI(htmlContent) {
    let inserido = false;

    // 1. Caso seja CKEditor (padrão do SEI)
    if (window.CKEDITOR && window.CKEDITOR.instances) {
      for (const instanceName in window.CKEDITOR.instances) {
        try {
          window.CKEDITOR.instances[instanceName].setData(htmlContent);
          inserido = true;
          console.log(`[LicitAI] HTML injetado no CKEditor instância: ${instanceName}`);
        } catch (e) {
          console.error('[LicitAI] Erro ao injetar no CKEditor:', e);
        }
      }
    }

    // 2. Caso seja iFrame editável
    if (!inserido) {
      const iframes = document.querySelectorAll('iframe');
      iframes.forEach((iframe) => {
        try {
          const doc = iframe.contentDocument || iframe.contentWindow.document;
          if (doc && (doc.designMode === 'on' || doc.body.contentEditable === 'true')) {
            doc.body.innerHTML = htmlContent;
            inserido = true;
            console.log('[LicitAI] HTML injetado no iFrame do SEI.');
          }
        } catch (e) {
          // iFrame cross-origin silenciado
        }
      });
    }

    // 3. Fallback: colar na área de transferência e alertar o usuário
    if (!inserido) {
      navigator.clipboard.writeText(htmlContent);
      alert('[LicitAI] O conteúdo do TR foi copiado para a área de transferência! Pressione Ctrl+V no editor do SEI para colar.');
    } else {
      alert('[LicitAI] Termo de Referência injetado no editor do SEI com sucesso!');
    }
  }

  // Ouvir mensagens enviadas do Popup da Extensão
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'INJECT_TR') {
      injetarHtmlNoSEI(request.html);
      sendResponse({ status: 'OK' });
    }
  });

  // Inicializar painel
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', criarPainelFlutuante);
  } else {
    criarPainelFlutuante();
  }
})();
