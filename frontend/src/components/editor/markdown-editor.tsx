"use client";

import { useEffect, useRef, useState } from "react";
import { Group, Panel, Separator } from "react-resizable-panels";
import type { WebsocketProvider } from "y-websocket";
import type * as Y from "yjs";
import { MarkdownPreview } from "@/components/editor/markdown-preview";
import { SourceEditor } from "@/components/editor/source-editor";

export function MarkdownEditor({
  text,
  provider,
  editable,
  serif,
  synced,
  initialMarkdown,
  onMarkdownChange,
}: {
  text: Y.Text;
  provider: WebsocketProvider;
  editable: boolean;
  serif: boolean;
  synced: boolean;
  initialMarkdown: string;
  onMarkdownChange: (markdown: string) => void;
}) {
  const [markdown, setMarkdown] = useState("");
  const seeded = useRef(false);

  // Preview mirrors the shared Y.Text (local edits, remote edits and the seed).
  useEffect(() => {
    const sync = () => setMarkdown(text.toString());
    sync();
    text.observe(sync);
    return () => text.unobserve(sync);
  }, [text]);

  // Seed a brand-new document from the cached Markdown, once, after first sync.
  useEffect(() => {
    if (!synced || seeded.current) return;
    seeded.current = true;
    if (editable && initialMarkdown.trim() && text.length === 0) {
      text.insert(0, initialMarkdown);
    }
  }, [synced, editable, initialMarkdown, text]);

  return (
    <Group orientation="horizontal" className="h-full min-h-0">
      <Panel defaultSize="50" minSize="25" className="min-h-0">
        <div className="flex h-full min-h-0 flex-col">
          <PaneLabel>{editable ? "Markdown" : "Markdown · read-only"}</PaneLabel>
          <div className="min-h-0 flex-1 pl-3">
            <SourceEditor
              text={text}
              provider={provider}
              editable={editable}
              onChange={onMarkdownChange}
            />
          </div>
        </div>
      </Panel>

      <Separator className="group relative w-px shrink-0 bg-line outline-none data-[separator-active]:bg-accent">
        <span className="absolute inset-y-0 -left-2 -right-2 transition-colors group-hover:bg-accent/10" />
      </Separator>

      <Panel defaultSize="50" minSize="25" className="min-h-0">
        <div className="flex h-full min-h-0 flex-col">
          <PaneLabel>Preview</PaneLabel>
          <div className="min-h-0 flex-1">
            <MarkdownPreview markdown={markdown} serif={serif} />
          </div>
        </div>
      </Panel>
    </Group>
  );
}

function PaneLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="shrink-0 px-4 pb-1 pt-3 text-[11px] font-medium uppercase tracking-[0.14em] text-ink-faint">
      {children}
    </div>
  );
}
