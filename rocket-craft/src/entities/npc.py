"""NPCs with walk animation and procedural sprites."""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING, Dict, Optional, Tuple

import pygame

from graphics.npc_sprites import NPCSpriteCache

if TYPE_CHECKING:
    from systems.town_map import TownMap


class NPC:
    """A small town character that walks, waits, and can be clicked."""

    def __init__(
        self,
        name: str,
        role: str,
        x: float,
        y: float,
        color: Tuple[int, int, int],
        seed: Optional[int] = None,
    ) -> None:
        self.name = name
        self.role = role
        self.x = x
        self.y = y
        self.color = color
        self.target_x = x
        self.target_y = y
        self.wait_time = random.uniform(1.0, 3.0)
        self.schedule: Dict[str, str] = {}
        self.dialogue = []
        self.radius = 12
        self._rng = random.Random(seed if seed is not None else hash(name) & 0xFFFF)
        self.walk_frame = 0
        self.facing_right = True
        self._anim_timer = 0.0
        self._sprite_cache = NPCSpriteCache()

    def set_schedule(self, schedule: Dict[str, str]) -> None:
        self.schedule = schedule

    def pick_random_target(self, town_map: "TownMap") -> None:
        point = town_map.pick_random_point(self._rng)
        if point is not None:
            self.target_x, self.target_y = point
        else:
            self.target_x, self.target_y = town_map.clamp_to_walkable(self.x, self.y)

    def update(self, dt: float, town_map: "TownMap") -> None:
        if self.wait_time > 0.0:
            self.wait_time -= dt
            return

        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.hypot(dx, dy)

        if dist < 5.0:
            self.pick_random_target(town_map)
            self.wait_time = self._rng.uniform(2.0, 5.0)
            return

        if abs(dx) > 0.5:
            self.facing_right = dx > 0

        speed = 58.0
        nx = self.x + (dx / dist) * speed * dt
        ny = self.y + (dy / dist) * speed * dt
        if town_map.is_walkable(nx, ny):
            self.x, self.y = nx, ny
            self._anim_timer += dt
            if self._anim_timer >= 0.12:
                self._anim_timer = 0.0
                self.walk_frame = (self.walk_frame + 1) % 4
        else:
            self.pick_random_target(town_map)
            self.wait_time = self._rng.uniform(1.0, 2.0)

    def contains_point(self, world_x: float, world_y: float) -> bool:
        dx = world_x - self.x
        dy = world_y - self.y
        return dx * dx + dy * dy <= (self.radius + 6) ** 2

    def render(self, screen: pygame.Surface, camera: object, font: pygame.font.Font) -> None:
        screen_x, screen_y = camera.world_to_screen(self.x, self.y)
        sprite = self._sprite_cache.get(self.role, self.walk_frame, self.facing_right)
        shadow = pygame.Surface((22, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 70), shadow.get_rect())
        screen.blit(shadow, (screen_x - 11, screen_y - 2))
        screen.blit(sprite, (screen_x - sprite.get_width() // 2, screen_y - sprite.get_height() + 2))

        name_surf = font.render(self.name, True, (255, 255, 255))
        name_rect = name_surf.get_rect(center=(screen_x, screen_y - sprite.get_height() - 6))
        shadow = font.render(self.name, True, (0, 0, 0))
        screen.blit(shadow, name_rect.move(1, 1))
        screen.blit(name_surf, name_rect)
