import type { Transition, Variants } from "motion/react";

export const ease: Transition = { duration: 0.2, ease: [0.22, 1, 0.36, 1] };
export const easeSlow: Transition = { duration: 0.32, ease: [0.22, 1, 0.36, 1] };

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: ease },
};

export const fade: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: ease },
};

export const dialogPanel: Variants = {
  hidden: { opacity: 0, scale: 0.98, y: 6 },
  show: { opacity: 1, scale: 1, y: 0, transition: ease },
  exit: { opacity: 0, scale: 0.98, y: 6, transition: { duration: 0.12 } },
};

export const listStagger: Variants = {
  show: { transition: { staggerChildren: 0.04 } },
};

// Follows a remote pointer smoothly.
export const pointerSpring: Transition = {
  type: "spring",
  stiffness: 700,
  damping: 40,
  mass: 0.6,
};
