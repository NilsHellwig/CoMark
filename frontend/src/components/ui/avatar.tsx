import { colorFor } from "@/lib/colors";
import { cn, initials } from "@/lib/utils";

export function Avatar({
  name,
  seed,
  color,
  size = 28,
  className,
  ring,
}: {
  name: string | null | undefined;
  seed: string;
  color?: string;
  size?: number;
  className?: string;
  ring?: boolean;
}) {
  const bg = color ?? colorFor(seed);
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full font-semibold text-white",
        ring && "ring-2 ring-surface",
        className,
      )}
      style={{
        width: size,
        height: size,
        backgroundColor: bg,
        fontSize: Math.round(size * 0.4),
      }}
      title={name ?? undefined}
    >
      {initials(name)}
    </span>
  );
}
