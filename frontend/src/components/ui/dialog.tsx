"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect } from "react";
import { dialogPanel, ease } from "@/lib/motion";
import { cn } from "@/lib/utils";

export function Dialog({
  open,
  onClose,
  title,
  description,
  children,
  className,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 pt-[12vh]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1, transition: ease }}
          exit={{ opacity: 0, transition: { duration: 0.12 } }}
        >
          <div
            className="fixed inset-0 bg-ink/20 backdrop-blur-[2px]"
            onClick={onClose}
            aria-hidden
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={title}
            variants={dialogPanel}
            initial="hidden"
            animate="show"
            exit="exit"
            className={cn(
              "relative w-full max-w-md rounded-lg border border-line bg-surface p-6 shadow-soft",
              className,
            )}
          >
            <h2 className="text-[15px] font-semibold tracking-tight text-ink">{title}</h2>
            {description ? (
              <p className="mt-1 text-[13px] text-ink-faint">{description}</p>
            ) : null}
            <div className="mt-4">{children}</div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
