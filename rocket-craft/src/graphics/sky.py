"""Procedural sky: gradient, sun, moon, clouds, stars."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pygame

from config import SCREEN_HEIGHT, SCREEN_WIDTH

Color = Tuple[int, int, int]


def _lerp_color(a: Color, b: Color, t: float) -> Color:
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _blend_sky_colors(light: float) -> Tuple[Color, Color]:
    """Return (top, bottom) sky colors from light level 0..1."""
    day_top, day_bot = (60, 120, 220), (180, 220, 255)
    sunset_top, sunset_bot = (180, 100, 60), (255, 180, 120)
    night_top, night_bot = (10, 10, 40), (30, 30, 80)

    if light > 0.55:
        t = (light - 0.55) / 0.45
        return _lerp_color(sunset_top, day_top, t), _lerp_color(sunset_bot, day_bot, t)
    if light > 0.25:
        t = (light - 0.25) / 0.3
        return _lerp_color(night_top, sunset_top, t), _lerp_color(night_bot, sunset_bot, t)
    return night_top, night_bot


@dataclass
class Cloud:
    x: float
    y: float
    width: float
    speed: float
    blobs: List[Tuple[float, float, float]]  # offset_x, offset_y, radius


@dataclass
class Star:
    x: int
    y: int
    color: Color
    size: int
    twinkle: bool
    phase: float
    alpha: int


class SkyRenderer:
    """Full-screen sky layer (viewport space, not world space)."""

    SUN_POS = (int(SCREEN_WIDTH * 0.7), int(SCREEN_HEIGHT * 0.3))
    MOON_POS = (int(SCREEN_WIDTH * 0.22), int(SCREEN_HEIGHT * 0.28))

    def __init__(self, seed: int = 77) -> None:
        self._rng = random.Random(seed)
        self._clouds = self._make_clouds()
        self._stars = self._make_stars()
        self._twinkle_timer = 0.0
        self._sky_cache: Optional[pygame.Surface] = None
        self._cache_light = -1.0

    def _make_clouds(self) -> List[Cloud]:
        clouds: List[Cloud] = []
        for _ in range(7):
            w = self._rng.uniform(50, 120)
            blobs = [
                (self._rng.uniform(-w * 0.3, w * 0.3), self._rng.uniform(-8, 8), self._rng.uniform(14, 28))
                for _ in range(self._rng.randint(3, 5))
            ]
            clouds.append(
                Cloud(
                    x=self._rng.uniform(0, SCREEN_WIDTH),
                    y=self._rng.uniform(40, SCREEN_HEIGHT * 0.42),
                    width=w,
                    speed=self._rng.uniform(10, 30) / 60.0,
                    blobs=blobs,
                )
            )
        return clouds

    def _make_stars(self) -> List[Star]:
        stars: List[Star] = []
        palette = [(255, 255, 255), (255, 255, 200), (200, 220, 255)]
        for _ in range(70):
            stars.append(
                Star(
                    x=self._rng.randint(0, SCREEN_WIDTH - 1),
                    y=self._rng.randint(0, int(SCREEN_HEIGHT * 0.55)),
                    color=self._rng.choice(palette),
                    size=self._rng.choice([1, 1, 2]),
                    twinkle=self._rng.random() < 0.2,
                    phase=self._rng.uniform(0, 6.28),
                    alpha=self._rng.randint(180, 255),
                )
            )
        return stars

    def update(self, dt: float, light: float) -> None:
        for cloud in self._clouds:
            cloud.x += cloud.speed * dt * 60.0
            if cloud.x > SCREEN_WIDTH + cloud.width:
                cloud.x = -cloud.width
        self._twinkle_timer += dt
        if abs(light - self._cache_light) > 0.02:
            self._sky_cache = None

    def draw(self, screen: pygame.Surface, light: float) -> None:
        if self._sky_cache is None or abs(light - self._cache_light) > 0.02:
            self._sky_cache = self._render_sky_gradient(light)
            self._cache_light = light
        screen.blit(self._sky_cache, (0, 0))

        night = 1.0 - min(1.0, light / 0.35)
        day = min(1.0, max(0.0, (light - 0.35) / 0.45))

        if day > 0.05:
            self._draw_sun(screen, day)
        if night > 0.05:
            self._draw_moon(screen, night)
            self._draw_stars(screen, night)

        cloud_alpha = int(160 + 60 * light)
        for cloud in self._clouds:
            self._draw_cloud(screen, cloud, cloud_alpha)

    def _render_sky_gradient(self, light: float) -> pygame.Surface:
        top, bottom = _blend_sky_colors(light)
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for y in range(SCREEN_HEIGHT):
            t = y / max(1, SCREEN_HEIGHT - 1)
            color = _lerp_color(top, bottom, t)
            pygame.draw.line(surf, color, (0, y), (SCREEN_WIDTH, y))
        return surf

    def _draw_sun(self, screen: pygame.Surface, strength: float) -> None:
        sx, sy = self.SUN_POS
        layers = [
            (40, 30, (255, 240, 200)),
            (25, 60, (255, 250, 220)),
            (15, 255, (255, 255, 240)),
        ]
        for radius, alpha, color in layers:
            a = int(alpha * strength)
            glow = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*color, a), (radius + 2, radius + 2), radius)
            screen.blit(glow, (sx - radius - 2, sy - radius - 2))

    def _draw_moon(self, screen: pygame.Surface, strength: float) -> None:
        mx, my = self.MOON_POS
        for radius, alpha, color in ((38, 25, (180, 200, 255)), (22, 50, (200, 215, 235)), (14, 255, (220, 230, 245))):
            a = int(alpha * strength)
            glow = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*color, a), (radius + 2, radius + 2), radius)
            screen.blit(glow, (mx - radius - 2, my - radius - 2))
        pygame.draw.circle(screen, (210, 220, 235), (mx, my), 14)
        for dx, dy, r in ((-4, -2, 2), (5, 3, 1), (2, 5, 2)):
            pygame.draw.circle(screen, (170, 180, 200), (mx + dx, my + dy), r)

    def _draw_stars(self, screen: pygame.Surface, night_strength: float) -> None:
        for star in self._stars:
            alpha = star.alpha
            if star.twinkle:
                flicker = 0.55 + 0.45 * abs(math.sin(self._twinkle_timer * 2.5 + star.phase))
                alpha = int(alpha * flicker)
            alpha = int(alpha * night_strength)
            if alpha < 8:
                continue
            if star.size <= 1:
                screen.set_at((star.x, star.y), (*star.color, alpha))
            else:
                s = pygame.Surface((4, 4), pygame.SRCALPHA)
                pygame.draw.circle(s, (*star.color, alpha), (2, 2), 2)
                screen.blit(s, (star.x - 2, star.y - 2))

    def _draw_cloud(self, screen: pygame.Surface, cloud: Cloud, base_alpha: int) -> None:
        for ox, oy, radius in cloud.blobs:
            cx = int(cloud.x + ox)
            cy = int(cloud.y + oy)
            r = int(radius)
            puff = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(puff, (255, 255, 255, base_alpha), (r + 1, r + 1), r)
            screen.blit(puff, (cx - r - 1, cy - r - 1))
