import Link from "next/link";
import { cn } from "@/lib/utils";

export function Logo({ className, href = "/" }: { className?: string; href?: string }) {
  return (
    <Link
      href={href}
      className={cn(
        "inline-flex items-center gap-2 text-[15px] font-semibold tracking-tight text-ink",
        className,
      )}
    >
      <span
        aria-hidden
        className="grid h-6 w-6 place-items-center rounded-sm bg-accent text-[13px] font-bold text-accent-ink"
      >
        C
      </span>
      CoMark
    </Link>
  );
}
