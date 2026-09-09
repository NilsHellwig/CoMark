"use client";

import { useEffect, useState } from "react";
import type { WebsocketProvider } from "y-websocket";

export interface Peer {
  clientId: number;
  user?: { id?: string; name?: string; color?: string };
}

/** Live snapshot of every *other* client present in the room. */
export function usePeers(provider: WebsocketProvider | null): Peer[] {
  const [peers, setPeers] = useState<Peer[]>([]);

  useEffect(() => {
    if (!provider) return;
    const { awareness } = provider;

    const sync = () => {
      const next: Peer[] = [];
      awareness.getStates().forEach((state, clientId) => {
        if (clientId === awareness.clientID) return;
        next.push({ clientId, user: state.user });
      });
      setPeers(next);
    };

    sync();
    awareness.on("change", sync);
    return () => awareness.off("change", sync);
  }, [provider]);

  return peers;
}
