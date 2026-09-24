/**
 * Sanitiza HTML do TR antes de injetar no editor do SEI.
 * Sem atributos, sem script/iframe/img. Espelha html_sanitize.py.
 */
(function (root) {
  'use strict';

  const ALLOWED = new Set([
    'P', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'BR',
    'STRONG', 'B', 'EM', 'I', 'U', 'UL', 'OL', 'LI',
    'TABLE', 'THEAD', 'TBODY', 'TR', 'TH', 'TD',
    'BLOCKQUOTE', 'DIV', 'SPAN',
  ]);

  function sanitizeHtml(raw) {
    if (!raw) return '';
    const doc = new DOMParser().parseFromString(
      '<div id="licitai-root">' + raw + '</div>',
      'text/html',
    );
    const root = doc.getElementById('licitai-root');
    if (!root) return '';

    function walk(node) {
      Array.from(node.childNodes).forEach((child) => {
        if (child.nodeType === Node.COMMENT_NODE) {
          child.remove();
          return;
        }
        if (child.nodeType !== Node.ELEMENT_NODE) return;
        const tag = child.tagName;
        if (
          tag === 'SCRIPT' ||
          tag === 'STYLE' ||
          tag === 'IFRAME' ||
          tag === 'OBJECT' ||
          tag === 'EMBED' ||
          tag === 'LINK' ||
          tag === 'META' ||
          tag === 'IMG'
        ) {
          child.remove();
          return;
        }
        if (!ALLOWED.has(tag)) {
          const parent = child.parentNode;
          while (child.firstChild) parent.insertBefore(child.firstChild, child);
          child.remove();
          return;
        }
        Array.from(child.attributes).forEach((attr) => {
          child.removeAttribute(attr.name);
        });
        walk(child);
      });
    }

    walk(root);
    return root.innerHTML;
  }

  function escapeText(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  root.LicitAISanitize = { sanitizeHtml, escapeText };
})(typeof window !== 'undefined' ? window : globalThis);
