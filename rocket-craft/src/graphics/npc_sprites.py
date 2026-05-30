"""Procedural NPC sprites with 4-frame walk cycles."""

from __future__ import annotations

from typing import Dict, Tuple

import pygame

Color = Tuple[int, int, int]

ROLE_MAP = {
    "Dr. Chen": "chen",
    "Scientist": "chen",
    "Bob": "bob",
    "Engineer": "bob",
    "Maria": "maria",
    "Mission Control": "maria",
    "Old Man Jenkins": "jenkins",
}

LEG_OFFSETS = [(0, 0), (3, -2), (0, 0), (-3, -2)]


def _flip(surf: pygame.Surface, facing_right: bool) -> pygame.Surface:
    if facing_right:
        return surf
    return pygame.transform.flip(surf, True, False)


def draw_npc(role: str, frame: int, facing_right: bool = True) -> pygame.Surface:
    """Draw one walk frame (24x36)."""
    key = ROLE_MAP.get(role, role.lower())
    drawers = {
        "chen": _draw_chen,
        "bob": _draw_bob,
        "maria": _draw_maria,
        "jenkins": _draw_jenkins,
    }
    drawer = drawers.get(key, _draw_bob)
    surf = drawer(frame % 4)
    return _flip(surf, facing_right)


class NPCSpriteCache:
    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, int, bool], pygame.Surface] = {}

    def get(self, role: str, frame: int, facing_right: bool) -> pygame.Surface:
        key = (ROLE_MAP.get(role, role), frame % 4, facing_right)
        if key not in self._cache:
            self._cache[key] = draw_npc(role, frame % 4, facing_right)
        return self._cache[key]


def _draw_legs(surf: pygame.Surface, frame: int, pants: Color) -> None:
    ox, oy = LEG_OFFSETS[frame % 4]
    pygame.draw.rect(surf, pants, (6 + ox, 24 + oy, 5, 8))
    pygame.draw.rect(surf, pants, (13 + ox, 24 - oy, 5, 8))


def _draw_chen(frame: int) -> pygame.Surface:
    surf = pygame.Surface((24, 36), pygame.SRCALPHA)
    skin = (255, 200, 150)
    _draw_legs(surf, frame, (70, 72, 80))
    pygame.draw.rect(surf, (220, 220, 225), (5, 14, 14, 12))
    pygame.draw.line(surf, (180, 180, 190), (12, 14), (12, 24), 1)
    pygame.draw.circle(surf, skin, (12, 10), 6)
    pygame.draw.circle(surf, (30, 30, 35), (12, 8), 6, 1)
    pygame.draw.circle(surf, (40, 40, 48), (9, 9), 2)
    pygame.draw.circle(surf, (40, 40, 48), (15, 9), 2)
    pygame.draw.line(surf, (50, 50, 58), (8, 10), (16, 10), 1)
    return surf


def _draw_bob(frame: int) -> pygame.Surface:
    surf = pygame.Surface((24, 36), pygame.SRCALPHA)
    skin = (230, 180, 140)
    _draw_legs(surf, frame, (80, 70, 55))
    pygame.draw.rect(surf, (255, 140, 50), (5, 14, 14, 12))
    pygame.draw.line(surf, (120, 80, 40), (5, 19), (19, 19), 2)
    pygame.draw.circle(surf, skin, (12, 10), 6)
    pygame.draw.arc(surf, (255, 220, 50), (6, 2, 12, 8), 3.14, 6.28, 3)
    pygame.draw.circle(surf, (90, 60, 30), (12, 7), 5)
    return surf


def _draw_maria(frame: int) -> pygame.Surface:
    surf = pygame.Surface((24, 36), pygame.SRCALPHA)
    skin = (255, 210, 175)
    _draw_legs(surf, frame, (40, 50, 90))
    pygame.draw.rect(surf, (50, 70, 120), (5, 14, 14, 12))
    pygame.draw.rect(surf, (220, 180, 60), (10, 17, 4, 3))
    pygame.draw.circle(surf, skin, (12, 10), 6)
    pygame.draw.circle(surf, (240, 210, 90), (12, 6), 6)
    pygame.draw.line(surf, (60, 60, 68), (6, 11), (4, 14), 1)
    pygame.draw.line(surf, (60, 60, 68), (6, 12), (8, 15), 1)
    return surf


def _draw_jenkins(frame: int) -> pygame.Surface:
    surf = pygame.Surface((24, 36), pygame.SRCALPHA)
    skin = (240, 195, 160)
    _draw_legs(surf, frame, (75, 70, 65))
    pygame.draw.rect(surf, (235, 235, 240), (5, 15, 14, 10))
    pygame.draw.rect(surf, (130, 95, 65), (6, 15, 12, 11))
    pygame.draw.circle(surf, skin, (12, 10), 6)
    pygame.draw.ellipse(surf, (200, 200, 205), (8, 10, 8, 7))
    pygame.draw.arc(surf, (230, 230, 235), (7, 4, 10, 8), 0, 3.14, 2)
    pygame.draw.line(surf, (100, 70, 45), (18, 18), (21, 30), 2)
    return surf
