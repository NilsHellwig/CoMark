"use client";

import { Avatar } from "@/components/ui/avatar";
import type { Peer } from "@/components/presence/use-awareness";

export function AvatarStack({
  peers,
  self,
}: {
  peers: Peer[];
  self: { id: string; name: string; color: string };
}) {
  const others = new Map<string, { name: string; color: string }>();
  for (const p of peers) {
    const id = p.user?.id ?? `c${p.clientId}`;
    if (p.user && id !== self.id) {
      others.set(id, { name: p.user.name ?? "Guest", color: p.user.color ?? "#3B5B6B" });
    }
  }

  const entries = [
    { id: self.id, name: `${self.name} (you)`, color: self.color },
    ...[...others.entries()].map(([id, u]) => ({ id, ...u })),
  ];

  return (
    <div className="flex items-center -space-x-2">
      {entries.slice(0, 5).map((e) => (
        <Avatar key={e.id} name={e.name} seed={e.id} color={e.color} size={26} ring />
      ))}
      {entries.length > 5 ? (
        <span className="ml-3 text-[12px] text-ink-faint">+{entries.length - 5}</span>
      ) : null}
    </div>
  );
}
