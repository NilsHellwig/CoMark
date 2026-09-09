import type { CollabStatus } from "@/components/editor/use-collab-doc";
import { cn } from "@/lib/utils";

const map: Record<CollabStatus, { label: string; color: string }> = {
  connected: { label: "Live", color: "bg-ok" },
  connecting: { label: "Connecting", color: "bg-ink-faint animate-pulse" },
  disconnected: { label: "Offline", color: "bg-danger" },
};

export function ConnectionDot({ status }: { status: CollabStatus }) {
  const s = map[status];
  return (
    <span className="inline-flex items-center gap-1.5 text-[12px] text-ink-faint">
      <span className={cn("h-1.5 w-1.5 rounded-full", s.color)} />
      {s.label}
    </span>
  );
}
