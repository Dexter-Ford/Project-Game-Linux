"""Programmatic rocket sprites."""

from __future__ import annotations

import math
from typing import Dict, Tuple

import pygame

from simulation.rocket import Rocket


def generate_rocket_sprite(thrust: bool = False) -> pygame.Surface:
    surf = pygame.Surface((32, 64), pygame.SRCALPHA)
    pygame.draw.polygon(surf, (220, 60, 60), [(16, 0), (6, 16), (26, 16)])
    pygame.draw.rect(surf, (220, 224, 230), (9, 16, 14, 34), border_radius=2)
    pygame.draw.rect(surf, (30, 34, 44), (9, 16, 14, 34), 1, border_radius=2)
    pygame.draw.rect(surf, (80, 180, 230), (13, 22, 6, 6))
    pygame.draw.polygon(surf, (80, 84, 92), [(9, 44), (2, 58), (10, 52)])
    pygame.draw.polygon(surf, (80, 84, 92), [(23, 44), (30, 58), (22, 52)])
    pygame.draw.rect(surf, (60, 60, 66), (12, 50, 8, 6))
    if thrust:
        pygame.draw.polygon(surf, (255, 230, 60), [(12, 56), (20, 56), (16, 63)])
        pygame.draw.polygon(surf, (255, 140, 40), [(14, 56), (18, 56), (16, 61)])
    return surf


def sprite_rotation_degrees(dir_world_x: float, dir_world_y: float) -> float:
    return math.degrees(math.atan2(-dir_world_y, dir_world_x)) + 90.0


class RocketSpriteCache:
    def __init__(self) -> None:
        self._cache: Dict[bool, pygame.Surface] = {}

    def get(self, rocket: Rocket, thrust: bool) -> pygame.Surface:
        if thrust not in self._cache:
            self._cache[thrust] = generate_rocket_sprite(thrust)
        return self._cache[thrust]
