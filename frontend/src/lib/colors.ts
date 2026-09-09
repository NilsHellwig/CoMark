// Deterministic, muted presence colour from any stable id (user id, guest id).
// Kept byte-compatible with the backend `app/services/colors.py`.
export const PALETTE = [
  "#3B5B6B",
  "#7A6C5D",
  "#4C6B54",
  "#8A5A44",
  "#5C5470",
  "#A08A48",
  "#4A7A82",
  "#9A6A6A",
];

export function colorFor(seed: string): string {
  let h = 0;
  for (let i = 0; i < seed.length; i += 1) {
    h = (Math.imul(h, 31) + seed.charCodeAt(i)) >>> 0;
  }
  return PALETTE[h % PALETTE.length];
}
