"use client";

import { useEffect, useMemo, useState } from "react";
import { WebsocketProvider } from "y-websocket";
import * as Y from "yjs";

export type CollabStatus = "connecting" | "connected" | "disconnected";

export interface Identity {
  id: string;
  name: string;
  color: string;
}

export interface CollabDoc {
  doc: Y.Doc;
  text: Y.Text;
  provider: WebsocketProvider | null;
  status: CollabStatus;
  synced: boolean;
}

/** The Y.Text field the Markdown source lives in. */
export const MARKDOWN_FIELD = "markdown";

function wsBase(): string {
  // Local dev: the backend is a separate origin (set in .env). Production: unset,
  // so fall back to same-origin — Caddy routes /api/v1/collab to the backend.
  if (process.env.NEXT_PUBLIC_WS_BASE_URL) return process.env.NEXT_PUBLIC_WS_BASE_URL;
  if (typeof window !== "undefined") {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${window.location.host}`;
  }
  return "ws://localhost:8897";
}

export function useCollabDoc(documentId: string, identity: Identity): CollabDoc {
  // eslint-disable-next-line react-hooks/exhaustive-deps -- one Y.Doc per document
  const doc = useMemo(() => new Y.Doc(), [documentId]);
  const text = useMemo(() => doc.getText(MARKDOWN_FIELD), [doc]);
  const [provider, setProvider] = useState<WebsocketProvider | null>(null);
  const [status, setStatus] = useState<CollabStatus>("connecting");
  const [synced, setSynced] = useState(false);

  useEffect(() => {
    const p = new WebsocketProvider(`${wsBase()}/api/v1/collab`, documentId, doc);
    const onStatus = (e: { status: CollabStatus }) => setStatus(e.status);
    const onSync = (s: boolean) => setSynced(s);
    p.on("status", onStatus);
    p.on("sync", onSync);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- provider is an external resource created here
    setProvider(p);
    return () => {
      p.off("status", onStatus);
      p.off("sync", onSync);
      p.destroy();
      doc.destroy();
      setProvider(null);
    };
  }, [documentId, doc]);

  useEffect(() => {
    provider?.awareness.setLocalStateField("user", {
      id: identity.id,
      name: identity.name,
      color: identity.color,
      colorLight: `${identity.color}33`,
    });
  }, [provider, identity.id, identity.name, identity.color]);

  return { doc, text, provider, status, synced };
}
