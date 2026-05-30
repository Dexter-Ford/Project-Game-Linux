"""Walkable town map."""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import pygame


class TownMap:
    GROUND_Y = 205

    def __init__(self, width: int, height: int, blocked_rects: Optional[Sequence[pygame.Rect]] = None) -> None:
        self.width = width
        self.height = height
        self.blocked_rects: List[pygame.Rect] = list(blocked_rects or [])

    def is_walkable(self, x: float, y: float) -> bool:
        ix, iy = int(x), int(y)
        if ix < 8 or ix >= self.width - 8 or iy < self.GROUND_Y or iy >= self.height - 8:
            return False
        return not any(rect.collidepoint(ix, iy) for rect in self.blocked_rects)

    def pick_random_point(self, rng) -> Optional[Tuple[float, float]]:
        for _ in range(80):
            x = rng.randint(28, self.width - 28)
            y = rng.randint(self.GROUND_Y + 12, self.height - 28)
            if self.is_walkable(x, y):
                return float(x), float(y)
        return None

    def clamp_to_walkable(self, x: float, y: float) -> Tuple[float, float]:
        x = max(12.0, min(float(self.width - 12), x))
        y = max(float(self.GROUND_Y + 12), min(float(self.height - 12), y))
        if self.is_walkable(x, y):
            return x, y
        return float(self.width // 2), float(self.GROUND_Y + 80)
