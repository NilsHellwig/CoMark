"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

export function MarkdownPreview({
  markdown,
  serif,
}: {
  markdown: string;
  serif: boolean;
}) {
  return (
    <div className="h-full min-h-0 overflow-auto">
      <div
        className={cn("comark-prose mx-auto max-w-[68ch] px-8 py-6")}
        data-serif={String(serif)}
      >
        {markdown.trim() ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
        ) : (
          <p className="text-ink-faint">Nothing to preview yet.</p>
        )}
      </div>
    </div>
  );
}
