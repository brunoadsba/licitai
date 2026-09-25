/** Limpa e parte a resposta do Copiloto para leitura (sem UUID nem falha de agente). */

const UUID_RE =
  /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi;
const SOURCE_ID_RE = /\b(?:legal|analysis|correction|doc):[^\s,;)]+/gi;
const AGENT_FAIL_RE =
  /\b(?:juridico|tecnico|redacao|estrutural|orchestrator):(?:failed|parse_error|ok_empty|skipped)\b/gi;

export function sanitizeChatAnswer(text: string): string {
  return text
    .replace(SOURCE_ID_RE, '')
    .replace(AGENT_FAIL_RE, '')
    .replace(UUID_RE, '')
    .replace(/[ \t]{2,}/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

export type AnswerBlock =
  | { kind: 'heading'; text: string }
  | { kind: 'paragraph'; text: string }
  | { kind: 'list'; items: string[] };

const HEADING_RE = /^(?:\*\*(.+?)\*\*|#{1,3}\s+(.+))$/;

export function parseAnswerBlocks(text: string): AnswerBlock[] {
  const clean = sanitizeChatAnswer(text);
  if (!clean) return [];

  const blocks: AnswerBlock[] = [];
  let list: string[] = [];
  let paragraph: string[] = [];

  const flushList = () => {
    if (list.length) {
      blocks.push({ kind: 'list', items: list });
      list = [];
    }
  };
  const flushParagraph = () => {
    const joined = paragraph.join(' ').trim();
    if (joined) blocks.push({ kind: 'paragraph', text: joined });
    paragraph = [];
  };

  for (const raw of clean.split('\n')) {
    const line = raw.trim();
    if (!line) {
      flushList();
      flushParagraph();
      continue;
    }
    const heading = line.match(HEADING_RE);
    if (heading) {
      flushList();
      flushParagraph();
      blocks.push({ kind: 'heading', text: (heading[1] || heading[2]).trim() });
      continue;
    }
    if (/^[-*]\s+/.test(line)) {
      flushParagraph();
      list.push(line.replace(/^[-*]\s+/, '').trim());
      continue;
    }
    flushList();
    paragraph.push(line);
  }
  flushList();
  flushParagraph();
  return blocks;
}

export function looksLikeId(value: string | null | undefined): boolean {
  if (!value) return false;
  return (
    /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i.test(value) ||
    /\b(?:legal|analysis|correction|doc):/i.test(value)
  );
}
