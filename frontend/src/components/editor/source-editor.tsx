"use client";

import { markdown } from "@codemirror/lang-markdown";
import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { EditorState } from "@codemirror/state";
import {
  EditorView,
  drawSelection,
  highlightActiveLine,
  highlightActiveLineGutter,
  keymap,
  lineNumbers,
} from "@codemirror/view";
import { defaultKeymap, indentWithTab } from "@codemirror/commands";
import { tags as t } from "@lezer/highlight";
import { useEffect, useRef } from "react";
import type { WebsocketProvider } from "y-websocket";
import type * as Y from "yjs";
import { yCollab, yUndoManagerKeymap } from "y-codemirror.next";

const scandiTheme = EditorView.theme({
  "&": {
    color: "var(--ink)",
    backgroundColor: "transparent",
    fontSize: "13.5px",
    height: "100%",
  },
  ".cm-scroller": {
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
    lineHeight: "1.75",
    overflow: "auto",
    padding: "12px 0 40vh",
  },
  ".cm-content": { caretColor: "var(--ink)" },
  "&.cm-focused": { outline: "none" },
  ".cm-gutters": {
    backgroundColor: "transparent",
    color: "var(--ink-faint)",
    border: "none",
  },
  ".cm-activeLineGutter": { backgroundColor: "transparent", color: "var(--ink-soft)" },
  ".cm-activeLine": {
    backgroundColor: "color-mix(in srgb, var(--accent) 5%, transparent)",
  },
  ".cm-selectionBackground, ::selection": {
    backgroundColor: "color-mix(in srgb, var(--accent) 16%, transparent)",
  },
  "&.cm-focused .cm-selectionBackground": {
    backgroundColor: "color-mix(in srgb, var(--accent) 24%, transparent)",
  },
});

const mdHighlight = HighlightStyle.define([
  { tag: t.heading, fontWeight: "600", color: "var(--ink)" },
  { tag: t.strong, fontWeight: "700", color: "var(--ink)" },
  { tag: t.emphasis, fontStyle: "italic" },
  { tag: t.link, color: "var(--accent)" },
  { tag: t.url, color: "var(--ink-faint)" },
  { tag: t.monospace, color: "var(--ink-soft)" },
  { tag: t.quote, color: "var(--ink-soft)" },
  { tag: [t.list, t.contentSeparator], color: "var(--ink-faint)" },
  { tag: [t.processingInstruction, t.punctuation], color: "var(--ink-faint)" },
]);

export function SourceEditor({
  text,
  provider,
  editable,
  onChange,
}: {
  text: Y.Text;
  provider: WebsocketProvider;
  editable: boolean;
  onChange: (markdown: string) => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);

  useEffect(() => {
    if (!host.current) return;

    const view = new EditorView({
      parent: host.current,
      state: EditorState.create({
        doc: text.toString(),
        extensions: [
          lineNumbers(),
          highlightActiveLine(),
          highlightActiveLineGutter(),
          drawSelection(),
          EditorView.lineWrapping,
          syntaxHighlighting(mdHighlight),
          markdown(),
          keymap.of([...yUndoManagerKeymap, ...defaultKeymap, indentWithTab]),
          yCollab(text, provider.awareness),
          scandiTheme,
          EditorView.editable.of(editable),
          EditorState.readOnly.of(!editable),
          EditorView.updateListener.of((u) => {
            if (u.docChanged) onChange(u.state.doc.toString());
          }),
        ],
      }),
    });
    viewRef.current = view;
    return () => {
      view.destroy();
      viewRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- onChange is stable enough; rebuild on doc/provider/role
  }, [text, provider, editable]);

  return <div ref={host} className="h-full min-h-0 overflow-hidden" />;
}
