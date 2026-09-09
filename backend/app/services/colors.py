from __future__ import annotations

# Muted, Scandinavian-leaning presence palette (shared with the frontend).
PALETTE = (
    "#3B5B6B",
    "#7A6C5D",
    "#4C6B54",
    "#8A5A44",
    "#5C5470",
    "#A08A48",
    "#4A7A82",
    "#9A6A6A",
)


def color_for(seed: str) -> str:
    h = 0
    for ch in seed:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return PALETTE[h % len(PALETTE)]
