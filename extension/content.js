/**
 * Injeta HTML sanitizado do TR no editor do SEI (CKEditor / iframe).
 */
(function () {
  'use strict';

  function criarPainelFlutuante() {
    if (document.getElementById('licitai-floating-panel')) return;

    const panel = document.createElement('div');
    panel.id = 'licitai-floating-panel';
    panel.style.cssText =
      'position:fixed;bottom:20px;right:20px;z-index:999999;background:#0f172a;color:#fff;' +
      'border:1px solid #334155;border-radius:12px;padding:12px 16px;' +
      'font-family:system-ui,sans-serif;box-shadow:0 10px 25px -5px rgba(0,0,0,.5);' +
      'display:flex;align-items:center;gap:10px;';

    const title = document.createElement('div');
    title.style.fontSize = '12px';
    title.style.fontWeight = 'bold';
    title.textContent = 'LicitAI no SEI';

    const hint = document.createElement('div');
    hint.style.fontSize = '10px';
    hint.style.color = '#94a3b8';
    hint.textContent = 'Clique no ícone da extensão para injetar TR';

    const textWrap = document.createElement('div');
    textWrap.appendChild(title);
    textWrap.appendChild(hint);

    const close = document.createElement('button');
    close.type = 'button';
    close.textContent = 'x';
    close.style.cssText =
      'background:none;border:none;color:#94a3b8;cursor:pointer;font-weight:bold;margin-left:8px;';
    close.addEventListener('click', () => {
      panel.style.display = 'none';
    });

    panel.appendChild(textWrap);
    panel.appendChild(close);
    document.body.appendChild(panel);
  }

  function injetarHtmlNoSEI(htmlContent) {
    const safe = (window.LicitAISanitize || { sanitizeHtml: () => '' }).sanitizeHtml(
      htmlContent,
    );
    let inserido = false;

    if (window.CKEDITOR && window.CKEDITOR.instances) {
      for (const instanceName in window.CKEDITOR.instances) {
        try {
          window.CKEDITOR.instances[instanceName].setData(safe);
          inserido = true;
        } catch (e) {
          console.error('[LicitAI] Erro ao injetar no CKEditor:', e);
        }
      }
    }

    if (!inserido) {
      document.querySelectorAll('iframe').forEach((iframe) => {
        try {
          const doc = iframe.contentDocument || iframe.contentWindow.document;
          if (doc && (doc.designMode === 'on' || doc.body.contentEditable === 'true')) {
            doc.body.innerHTML = safe;
            inserido = true;
          }
        } catch (e) {
          /* iframe cross-origin */
        }
      });
    }

    if (!inserido) {
      navigator.clipboard.writeText(safe);
      alert(
        '[LicitAI] O conteúdo sanitizado foi copiado. Cole no editor do SEI com Ctrl+V.',
      );
    }
  }

  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'INJECT_TR') {
      injetarHtmlNoSEI(request.html);
      sendResponse({ status: 'OK' });
    }
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', criarPainelFlutuante);
  } else {
    criarPainelFlutuante();
  }
})();
