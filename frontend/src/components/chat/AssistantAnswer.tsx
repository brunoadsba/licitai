'use client';

import { parseAnswerBlocks } from '@/lib/chatAnswer';

export default function AssistantAnswer({ content }: { content: string }) {
  const blocks = parseAnswerBlocks(content);
  if (blocks.length === 0) {
    return <p className="whitespace-pre-wrap text-content-secondary">{content}</p>;
  }

  return (
    <div className="space-y-2.5 text-content-secondary">
      {blocks.map((block, index) => {
        if (block.kind === 'heading') {
          return (
            <h3
              key={`h-${index}`}
              className="text-xs font-semibold uppercase tracking-wide text-content-primary"
            >
              {block.text}
            </h3>
          );
        }
        if (block.kind === 'list') {
          return (
            <ol key={`l-${index}`} className="list-decimal space-y-1 pl-4 text-[15px] leading-relaxed">
              {block.items.map((item, itemIndex) => (
                <li key={`${index}-${itemIndex}`}>{item}</li>
              ))}
            </ol>
          );
        }
        return (
          <p key={`p-${index}`} className="text-[15px] leading-relaxed">
            {block.text}
          </p>
        );
      })}
    </div>
  );
}
