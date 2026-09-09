"use client";

import { useMutation } from "@tanstack/react-query";
import { useCallback, useEffect, useRef } from "react";
import { putDocumentContentMutation } from "@/lib/api";

/** Debounced push of the editor's Markdown to the server-side cache (editors only). */
export function useMarkdownSync(documentId: string, enabled: boolean) {
  const mutation = useMutation(putDocumentContentMutation());
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latest = useRef("");

  const push = useCallback(
    (markdown: string) => {
      if (!enabled) return;
      latest.current = markdown;
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => {
        mutation.mutate({
          path: { document_id: documentId },
          body: { markdown: latest.current },
        });
      }, 1500);
    },
    [documentId, enabled, mutation],
  );

  useEffect(() => () => void (timer.current && clearTimeout(timer.current)), []);

  return push;
}
