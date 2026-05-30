"""Procedural trees, grass patches, and flowers."""

from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple

import pygame

from systems.town_map import TownMap

Color = Tuple[int, int, int]
TreeType = str  # oak, pine, bushy, birch


def _tree_shadow(surf: pygame.Surface, base_x: int, base_y: int, width: int) -> None:
    sh = pygame.Surface((width + 16, 14), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 60), sh.get_rect())
    surf.blit(sh, (base_x - 8, base_y - 6))


def draw_tree(tree_type: TreeType, x: int = 0, y: int = 0, scale: float = 1.0) -> pygame.Surface:
    drawers = {
        "oak": _draw_tree_oak,
        "pine": _draw_tree_pine,
        "bushy": _draw_tree_bushy,
        "birch": _draw_tree_birch,
    }
    base = drawers.get(tree_type, _draw_tree_oak)(x, y)
    if abs(scale - 1.0) < 0.03:
        return base
    w = max(1, int(base.get_width() * scale))
    h = max(1, int(base.get_height() * scale))
    return pygame.transform.smoothscale(base, (w, h))


def _draw_tree_oak(x: int, y: int) -> pygame.Surface:
    w, h = 48, 72
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    _tree_shadow(surf, w // 2, h - 4, 32)
    pygame.draw.rect(surf, (92, 58, 32), (w // 2 - 2, h - 28, 4, 22))
    pygame.draw.line(surf, (70, 42, 24), (w // 2, h - 26), (w // 2, h - 8), 1)
    cx, cy = w // 2, h - 38
    pygame.draw.circle(surf, (48, 130, 52), (cx, cy), 22)
    pygame.draw.circle(surf, (36, 108, 42), (cx, cy + 4), 20)
    for ox, oy, r in ((-10, -8, 8), (8, -10, 7), (-4, 6, 6)):
        pygame.draw.circle(surf, (72, 160, 68), (cx + ox, cy + oy), r)
    return surf


def _draw_tree_pine(x: int, y: int) -> pygame.Surface:
    w, h = 40, 68
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    _tree_shadow(surf, w // 2, h - 4, 28)
    pygame.draw.rect(surf, (88, 54, 30), (w // 2 - 1, h - 22, 3, 16))
    cx = w // 2
    layers = [(26, h - 24, (34, 100, 44)), (20, h - 36, (40, 118, 50)), (14, h - 48, (48, 132, 56))]
    for half_w, top_y, color in layers:
        pts = [(cx, top_y - 14), (cx - half_w, top_y + 10), (cx + half_w, top_y + 10)]
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.line(surf, (28, 80, 36), (cx - half_w, top_y + 10), (cx + half_w, top_y + 10), 1)
    return surf


def _draw_tree_bushy(x: int, y: int) -> pygame.Surface:
    w, h = 44, 56
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    _tree_shadow(surf, w // 2, h - 4, 30)
    pygame.draw.rect(surf, (82, 50, 28), (w // 2 - 1, h - 16, 3, 10))
    greens = ((52, 128, 55), (44, 110, 48), (64, 145, 62), (38, 95, 42))
    radii = (9, 10, 8, 11, 7, 8)
    for i, (ox, oy) in enumerate(((-10, -6), (6, -8), (0, 2), (-6, 8), (10, 6), (2, -12))):
        pygame.draw.circle(surf, greens[i % len(greens)], (w // 2 + ox, h - 28 + oy), radii[i])
    return surf


def _draw_tree_birch(x: int, y: int) -> pygame.Surface:
    w, h = 36, 76
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    _tree_shadow(surf, w // 2, h - 4, 22)
    trunk = pygame.Rect(w // 2 - 2, h - 42, 4, 34)
    pygame.draw.rect(surf, (230, 228, 220), trunk)
    for mark_y in range(h - 40, h - 12, 6):
        pygame.draw.line(surf, (40, 40, 44), (trunk.left, mark_y), (trunk.right, mark_y), 1)
    for ox, oy in ((-6, -32), (4, -34), (-2, -38), (5, -30)):
        pygame.draw.ellipse(surf, (55, 140, 58), (w // 2 + ox - 5, h - 50 + oy, 10, 8))
    return surf


def draw_grass_patch(x: int = 0, y: int = 0) -> pygame.Surface:
    rng = random.Random((x * 928371) ^ (y * 689287))
    surf = pygame.Surface((16, 10), pygame.SRCALPHA)
    greens = ((72, 140, 58), (58, 120, 48), (88, 160, 72))
    for _ in range(rng.randint(5, 8)):
        gx = rng.randint(1, 13)
        gh = rng.randint(4, 8)
        color = rng.choice(greens)
        pygame.draw.line(surf, color, (gx, 9), (gx + rng.randint(-1, 1), 9 - gh), 1)
    return surf


def draw_flower(x: int = 0, y: int = 0) -> pygame.Surface:
    rng = random.Random((x * 1231) ^ (y * 9973))
    surf = pygame.Surface((8, 12), pygame.SRCALPHA)
    colors = ((255, 230, 60), (220, 60, 70), (255, 255, 255), (180, 100, 220))
    pygame.draw.line(surf, (50, 120, 45), (4, 11), (4, 5), 1)
    pygame.draw.circle(surf, rng.choice(colors), (4, 4), 3)
    return surf


class VegetationManager:
    """Places trees and ground cover from a seeded layout."""

    def __init__(
        self,
        town_map: TownMap,
        bounds: Tuple[int, int],
        blocked_rects: List[pygame.Rect],
        seed: int = 42,
        path_points: Optional[List[Tuple[int, int]]] = None,
    ) -> None:
        self.town_map = town_map
        self.bounds = bounds
        self.path_points = path_points or [(170, 390), (420, 430), (620, 240), (620, 410), (420, 430), (420, 325)]
        self._rng = random.Random(seed)
        self.trees: List[Tuple[TreeType, float, float, float]] = []
        self.ground: List[Tuple[str, float, float]] = []
        self._generate(blocked_rects)

    def _near_path(self, wx: float, wy: float, margin: float = 28.0) -> bool:
        pts = self.path_points
        for i in range(len(pts) - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
            dx, dy = x2 - x1, y2 - y1
            length_sq = dx * dx + dy * dy
            if length_sq < 1:
                continue
            t = max(0, min(1, ((wx - x1) * dx + (wy - y1) * dy) / length_sq))
            px, py = x1 + t * dx, y1 + t * dy
            if math.hypot(wx - px, wy - py) < margin:
                return True
        return False

    def _blocked_by_building(self, wx: float, wy: float, rects: List[pygame.Rect]) -> bool:
        for rect in rects:
            if rect.inflate(24, 24).collidepoint(wx, wy):
                return True
        return False

    def _generate(self, blocked_rects: List[pygame.Rect]) -> None:
        types: List[TreeType] = ["oak", "pine", "bushy", "birch"]
        attempts = 0
        target_trees = 54 if self.bounds[0] > 1000 else 28
        while len(self.trees) < target_trees and attempts < 1200:
            attempts += 1
            wx = self._rng.uniform(40, self.bounds[0] - 40)
            wy = self._rng.uniform(TownMap.GROUND_Y + 15, self.bounds[1] - 30)
            if not self.town_map.is_walkable(wx, wy):
                continue
            if self._near_path(wx, wy, 36):
                continue
            if self._blocked_by_building(wx, wy, blocked_rects):
                continue
            self.trees.append((self._rng.choice(types), wx, wy, self._rng.uniform(0.75, 1.15)))

        ground_count = 900 if self.bounds[0] > 1000 else 420
        for _ in range(ground_count):
            wx = self._rng.uniform(20, self.bounds[0] - 20)
            wy = self._rng.uniform(TownMap.GROUND_Y + 5, self.bounds[1] - 15)
            if not self.town_map.is_walkable(wx, wy):
                continue
            if self._near_path(wx, wy, 22):
                continue
            if self._blocked_by_building(wx, wy, blocked_rects):
                continue
            roll = self._rng.random()
            if roll < 0.6:
                self.ground.append(("grass", wx, wy))
            elif roll < 0.7:
                self.ground.append(("flower", wx, wy))

    def draw(
        self,
        screen: pygame.Surface,
        camera: object,
        light: float,
    ) -> None:
        # Ground decor back
        for kind, wx, wy in self.ground:
            sx, sy = camera.world_to_screen(wx, wy)
            if sx < -20 or sy < -20 or sx > screen.get_width() + 20:
                continue
            if kind == "grass":
                patch = draw_grass_patch(int(wx), int(wy))
                screen.blit(patch, (sx, sy - 6))
            else:
                flower = draw_flower(int(wx), int(wy))
                screen.blit(flower, (sx - 4, sy - 10))

        # Trees sorted by y
        ordered = sorted(self.trees, key=lambda t: t[2])
        for tree_type, wx, wy, scale in ordered:
            sx, sy = camera.world_to_screen(wx, wy)
            if sx < -80 or sy < -100:
                continue
            tree_surf = draw_tree(tree_type, scale=scale)
            screen.blit(tree_surf, (sx - tree_surf.get_width() // 2, sy - tree_surf.get_height() + 4))

        # Darken vegetation slightly at night
        if light < 0.45:
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            overlay.fill((20, 30, 60, int(50 * (1.0 - light / 0.45))))
            screen.blit(overlay, (0, 0))
