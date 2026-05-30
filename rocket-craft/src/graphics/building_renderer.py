"""
RCT-style programmatic buildings: gradients, depth, shadows, no external assets.
"""

from __future__ import annotations

import math
from typing import Dict, Optional, Tuple

import pygame

Color = Tuple[int, int, int]


def _clamp(v: float, lo: float = 0.0, hi: float = 255.0) -> int:
    return int(max(lo, min(hi, v)))


def _lerp(a: int, b: int, t: float) -> int:
    return _clamp(a + (b - a) * t)


def _lerp_color(c1: Color, c2: Color, t: float) -> Color:
    return (_lerp(c1[0], c2[0], t), _lerp(c1[1], c2[1], t), _lerp(c1[2], c2[2], t))


def _vertical_gradient_rect(
    surf: pygame.Surface,
    rect: pygame.Rect,
    top: Color,
    bottom: Color,
) -> None:
    if rect.height <= 0:
        return
    for row in range(rect.height):
        t = row / max(1, rect.height - 1)
        color = _lerp_color(top, bottom, t)
        pygame.draw.line(surf, color, (rect.left, rect.top + row), (rect.right - 1, rect.top + row))


def _shaded_wall_gradient(
    surf: pygame.Surface,
    rect: pygame.Rect,
    base: Color,
) -> None:
    """Top 20% lighter, bottom 10% darker than base."""
    top = (
        _clamp(base[0] * 1.2),
        _clamp(base[1] * 1.2),
        _clamp(base[2] * 1.2),
    )
    bottom = (
        _clamp(base[0] * 0.9),
        _clamp(base[1] * 0.9),
        _clamp(base[2] * 0.9),
    )
    _vertical_gradient_rect(surf, rect, top, bottom)


def _draw_window(
    surf: pygame.Surface,
    rect: pygame.Rect,
    is_night: bool,
    day_fill: Color = (140, 180, 220),
) -> None:
    if is_night:
        glow_rect = rect.inflate(6, 6)
        glow = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(glow, (255, 220, 150, 40), glow.get_rect(), border_radius=2)
        surf.blit(glow, (glow_rect.x, glow_rect.y))
        win = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(win, (255, 220, 150, 200), win.get_rect(), border_radius=1)
        surf.blit(win, rect.topleft)
    else:
        pygame.draw.rect(surf, day_fill, rect, border_radius=1)
        pygame.draw.rect(surf, (245, 248, 252), rect, 1, border_radius=1)
        pygame.draw.line(
            surf,
            (255, 255, 255),
            (rect.left + 2, rect.top + 2),
            (rect.left + max(3, rect.width // 2), rect.top + 2),
            1,
        )


def _draw_ground_shadow(
    surf: pygame.Surface,
    width: int,
    ground_y: int,
    alpha: int = 80,
    spread: int = 20,
) -> None:
    shadow_h = max(12, width // 12)
    shadow = pygame.Surface((width + spread, shadow_h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, alpha), shadow.get_rect())
    surf.blit(shadow, (-spread // 2, ground_y - shadow_h // 2))


def _scale_surface(source: pygame.Surface, scale: float) -> pygame.Surface:
    if abs(scale - 1.0) < 0.02:
        return source
    w = max(1, int(source.get_width() * scale))
    h = max(1, int(source.get_height() * scale))
    return pygame.transform.smoothscale(source, (w, h))


class BuildingRenderer:
    """Cached procedural building sprites for the town screen."""

    BASE_SIZES = {
        "hangar": (200, 140),
        "research": (120, 100),
        "contracts": (140, 90),
        "shop": (90, 70),
        "house": (120, 80),
        "home_bob": (115, 78),
        "home_chen": (115, 78),
        "home_maria": (115, 78),
        "home_jenkins": (115, 78),
    }

    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, float, bool], pygame.Surface] = {}

    def surface_for(
        self,
        building_type: str,
        scale: float = 1.0,
        is_night: bool = False,
    ) -> pygame.Surface:
        key = (building_type, round(scale, 3), is_night)
        if key not in self._cache:
            drawer = {
                "hangar": draw_hangar,
                "research": draw_research_lab,
                "contracts": draw_mission_control,
                "shop": draw_supply_depot,
                "house": draw_house,
                "home_bob": draw_home_bob,
                "home_chen": draw_home_chen,
                "home_maria": draw_home_maria,
                "home_jenkins": draw_home_jenkins,
            }.get(building_type, draw_supply_depot)
            base_w, base_h = self.BASE_SIZES.get(building_type, (100, 80))
            self._cache[key] = drawer(0, 0, scale, base_w, base_h, is_night=is_night)
        return self._cache[key]

    def draw_at(
        self,
        screen: pygame.Surface,
        building_type: str,
        screen_x: int,
        screen_y: int,
        scale: float = 1.0,
        anchor_bottom: bool = True,
        is_night: bool = False,
    ) -> pygame.Rect:
        """Blit building with bottom-left at (screen_x, screen_y). Returns visual rect."""
        surf = self.surface_for(building_type, scale, is_night=is_night)
        if anchor_bottom:
            pos = (screen_x, screen_y - surf.get_height())
        else:
            pos = (screen_x, screen_y)
        screen.blit(surf, pos)
        return surf.get_rect(topleft=pos)

    def clear_cache(self) -> None:
        self._cache.clear()


def draw_hangar(
    x: int = 0,
    y: int = 0,
    scale: float = 1.0,
    width: int = 200,
    height: int = 140,
    is_night: bool = False,
) -> pygame.Surface:
    """Industrial hangar — curved roof, sliding door, warning stripes."""
    pad_bottom = 18
    total_h = height + pad_bottom
    surf = pygame.Surface((width + 24, total_h), pygame.SRCALPHA)
    ox, oy = 12 + x, y

    _draw_ground_shadow(surf, width, total_h - 6, alpha=90, spread=28)

    wall_top = oy + 38
    wall_bottom = oy + height - 8
    wall_rect = pygame.Rect(ox + 14, wall_top, width - 28, wall_bottom - wall_top)

    _shaded_wall_gradient(surf, wall_rect, (148, 150, 156))

    # Panel seams
    for col in range(ox + 28, ox + width - 28, 34):
        pygame.draw.line(surf, (100, 102, 108), (col, wall_top), (col, wall_bottom), 1)
    for row in range(wall_top + 18, wall_bottom, 22):
        pygame.draw.line(surf, (95, 97, 103), (wall_rect.left, row), (wall_rect.right, row), 1)

    # Side depth strips (darker edges)
    pygame.draw.rect(surf, (88, 90, 96), (wall_rect.left, wall_top, 6, wall_rect.height))
    pygame.draw.rect(surf, (72, 74, 80), (wall_rect.right - 5, wall_top, 5, wall_rect.height))

    # Curved roof (arch)
    roof_rect = pygame.Rect(ox + 8, oy + 12, width - 16, 72)
    pygame.draw.ellipse(surf, (108, 110, 116), roof_rect)
    pygame.draw.arc(surf, (78, 80, 86), roof_rect, math.pi, 2 * math.pi, 6)
    pygame.draw.arc(surf, (140, 142, 148), roof_rect, math.pi * 1.05, math.pi * 1.95, 2)
    for rib_x in range(ox + 24, ox + width - 24, 20):
        pygame.draw.line(surf, (90, 92, 98), (rib_x, oy + 28), (rib_x, oy + 52), 1)

    # Roof highlight ridge
    pygame.draw.line(
        surf,
        (150, 152, 158),
        (ox + width // 2 - 30, oy + 28),
        (ox + width // 2 + 30, oy + 28),
        2,
    )

    # Large sliding door
    door_w, door_h = 56, 52
    door_x = ox + width // 2 - door_w // 2
    door_y = wall_bottom - door_h
    pygame.draw.rect(surf, (52, 54, 58), (door_x, door_y, door_w, door_h), border_radius=2)
    pygame.draw.rect(surf, (38, 40, 44), (door_x, door_y, door_w, door_h), 2, border_radius=2)
    for i in range(1, 5):
        lx = door_x + i * (door_w // 5)
        pygame.draw.line(surf, (70, 72, 78), (lx, door_y + 4), (lx, door_y + door_h - 4), 2)

    # Warning stripes
    stripe_y = door_y - 12
    for i in range(5):
        color = (255, 200, 40) if i % 2 == 0 else (42, 42, 46)
        pygame.draw.rect(surf, color, (door_x - 8 + i * 14, stripe_y, 14, 10))

    for wx in (ox + 30, ox + width - 42):
        _draw_window(surf, pygame.Rect(wx, wall_top + 16, 10, 12), is_night, (120, 150, 180))

    # Yellow accent lights
    for lx in (ox + 22, ox + width - 30):
        pygame.draw.circle(surf, (255, 220, 60), (lx, wall_top + 8), 4)
        pygame.draw.circle(surf, (255, 255, 180), (lx, wall_top + 8), 2)

    return _scale_surface(surf, scale)


def draw_research_lab(
    x: int = 0,
    y: int = 0,
    scale: float = 1.0,
    width: int = 120,
    height: int = 100,
    is_night: bool = False,
) -> pygame.Surface:
    """Modern lab — flat roof, antenna, blue glass, chimney smoke."""
    pad_bottom = 14
    total_h = height + pad_bottom
    surf = pygame.Surface((width + 20, total_h), pygame.SRCALPHA)
    ox, oy = 10 + x, y

    _draw_ground_shadow(surf, width, total_h - 5, alpha=70, spread=18)

    wall_top = oy + 28
    wall_bottom = oy + height - 6
    wall_rect = pygame.Rect(ox + 8, wall_top, width - 16, wall_bottom - wall_top)

    _shaded_wall_gradient(surf, wall_rect, (230, 235, 242))

    # Flat roof slab
    roof = pygame.Rect(ox + 4, oy + 16, width - 8, 18)
    pygame.draw.rect(surf, (190, 198, 210), roof, border_radius=2)
    pygame.draw.rect(surf, (160, 168, 180), roof, 2, border_radius=2)
    pygame.draw.line(surf, (220, 228, 238), (roof.left + 2, roof.top + 2), (roof.right - 2, roof.top + 2), 2)

    # Antenna / spire
    ax = ox + width - 22
    pygame.draw.line(surf, (140, 148, 160), (ax, oy + 4), (ax, oy + 20), 2)
    pygame.draw.circle(surf, (200, 80, 80), (ax, oy + 4), 3)

    for wy in range(wall_top + 12, wall_bottom - 20, 22):
        for wx in range(ox + 18, ox + width - 24, 26):
            _draw_window(surf, pygame.Rect(wx, wy, 18, 16), is_night, (120, 180, 240))

    # Door
    pygame.draw.rect(surf, (180, 188, 200), (ox + width // 2 - 10, wall_bottom - 22, 20, 22))
    pygame.draw.rect(surf, (100, 110, 125), (ox + width // 2 - 10, wall_bottom - 22, 20, 22), 1)

    # Chimney + smoke puffs
    ch_x, ch_y = ox + 18, wall_top - 4
    pygame.draw.rect(surf, (150, 158, 168), (ch_x, ch_y, 10, 14))
    for i, (dx, dy, r, alpha) in enumerate([(4, -8, 6, 50), (10, -16, 8, 40), (16, -24, 10, 28)]):
        puff = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(puff, (220, 225, 235, alpha), (r, r), r)
        surf.blit(puff, (ch_x + dx - r, ch_y + dy - r))

    return _scale_surface(surf, scale)


def draw_mission_control(
    x: int = 0,
    y: int = 0,
    scale: float = 1.0,
    width: int = 140,
    height: int = 90,
    is_night: bool = False,
) -> pygame.Surface:
    """Low bunker — many windows, satellite dish."""
    pad_bottom = 14
    total_h = height + pad_bottom
    surf = pygame.Surface((width + 30, total_h), pygame.SRCALPHA)
    ox, oy = 15 + x, y

    _draw_ground_shadow(surf, width, total_h - 5, alpha=85, spread=22)

    wall_top = oy + 22
    wall_bottom = oy + height - 4
    wall_rect = pygame.Rect(ox + 6, wall_top, width - 12, wall_bottom - wall_top)

    _shaded_wall_gradient(surf, wall_rect, (78, 84, 94))

    # Bunker berm (earth lip at base)
    berm = [
        (ox, wall_bottom),
        (ox + width, wall_bottom),
        (ox + width - 8, wall_bottom + 10),
        (ox + 8, wall_bottom + 10),
    ]
    pygame.draw.polygon(surf, (72, 88, 62), berm)

    # Flat reinforced roof
    pygame.draw.rect(surf, (70, 74, 82), (ox + 2, oy + 10, width - 4, 14))
    pygame.draw.line(surf, (110, 114, 122), (ox + 4, oy + 12), (ox + width - 4, oy + 12), 1)

    for wy in range(wall_top + 8, wall_bottom - 14, 14):
        for wx in range(ox + 14, ox + width - 20, 16):
            _draw_window(surf, pygame.Rect(wx, wy, 12, 10), is_night, (50, 120, 200))

    # Heavy door
    pygame.draw.rect(surf, (42, 46, 54), (ox + width // 2 - 14, wall_bottom - 20, 28, 20))
    pygame.draw.rect(surf, (28, 30, 36), (ox + width // 2 - 14, wall_bottom - 20, 28, 20), 2)

    # Satellite dish on roof
    dish_x = ox + width - 36
    dish_y = oy + 6
    pygame.draw.line(surf, (100, 104, 112), (dish_x, dish_y + 14), (dish_x, oy + 22), 2)
    pygame.draw.polygon(
        surf,
        (130, 136, 148),
        [
            (dish_x - 16, dish_y + 10),
            (dish_x, dish_y - 4),
            (dish_x + 16, dish_y + 10),
        ],
    )
    pygame.draw.arc(surf, (180, 190, 210), (dish_x - 14, dish_y, 28, 14), math.pi, 2 * math.pi, 2)

    return _scale_surface(surf, scale)


def draw_supply_depot(
    x: int = 0,
    y: int = 0,
    scale: float = 1.0,
    width: int = 90,
    height: int = 70,
    is_night: bool = False,
) -> pygame.Surface:
    """Warehouse — gable roof, wood walls, cream trim."""
    pad_bottom = 12
    total_h = height + pad_bottom
    surf = pygame.Surface((width + 16, total_h), pygame.SRCALPHA)
    ox, oy = 8 + x, y

    _draw_ground_shadow(surf, width, total_h - 4, alpha=75, spread=14)

    wall_top = oy + 26
    wall_bottom = oy + height - 4
    wall_rect = pygame.Rect(ox + 6, wall_top, width - 12, wall_bottom - wall_top)

    # Wood plank walls
    for row in range(wall_rect.height):
        t = row / max(1, wall_rect.height - 1)
        base = _lerp_color((168, 128, 88), (130, 96, 64), t)
        pygame.draw.line(
            surf,
            base,
            (wall_rect.left, wall_rect.top + row),
            (wall_rect.right, wall_rect.top + row),
        )
    for row in range(wall_top, wall_bottom, 10):
        pygame.draw.line(surf, (110, 82, 54), (wall_rect.left, row), (wall_rect.right, row), 1)

    peak_x = ox + width // 2
    peak_y = oy + 10
    pygame.draw.polygon(
        surf,
        (120, 48, 42),
        [(ox + 4, wall_top), (peak_x, peak_y), (ox + width - 4, wall_top)],
    )
    pygame.draw.polygon(
        surf,
        (150, 62, 52),
        [(ox + 8, wall_top - 2), (peak_x, peak_y + 4), (ox + width - 8, wall_top - 2)],
    )
    for tile_y in range(wall_top - 8, wall_top + 4, 5):
        pygame.draw.line(surf, (100, 40, 36), (ox + 10, tile_y), (ox + width - 10, tile_y), 1)

    # Cream trim band
    pygame.draw.rect(surf, (240, 232, 210), (ox + 5, wall_top - 3, width - 10, 5))

    _draw_window(surf, pygame.Rect(ox + width - 28, wall_top + 14, 16, 14), is_night, (200, 230, 255))
    pygame.draw.rect(surf, (70, 50, 38), (ox + 14, wall_bottom - 20, 18, 18))
    pygame.draw.circle(surf, (200, 180, 60), (ox + 28, wall_bottom - 10), 2)

    # Crate stack detail
    for cx in (ox + 50, ox + 62):
        pygame.draw.rect(surf, (150, 110, 70), (cx, wall_bottom - 16, 12, 12))
        pygame.draw.rect(surf, (100, 75, 48), (cx, wall_bottom - 16, 12, 12), 1)

    return _scale_surface(surf, scale)


def draw_house(
    x: int = 0,
    y: int = 0,
    scale: float = 1.0,
    width: int = 120,
    height: int = 80,
    is_night: bool = False,
) -> pygame.Surface:
    """Player cottage — red gable roof, chimney, one window, one door."""
    pad_bottom = 12
    total_h = height + pad_bottom
    surf = pygame.Surface((width + 16, total_h), pygame.SRCALPHA)
    ox, oy = 8 + x, y

    _draw_ground_shadow(surf, width, total_h - 4, alpha=75, spread=14)

    wall_top = oy + 28
    wall_bottom = oy + height - 4
    wall_rect = pygame.Rect(ox + 6, wall_top, width - 12, wall_bottom - wall_top)

    _shaded_wall_gradient(surf, wall_rect, (220, 210, 195))

    peak_x = ox + width // 2
    peak_y = oy + 8
    pygame.draw.polygon(
        surf,
        (168, 42, 38),
        [(ox + 4, wall_top), (peak_x, peak_y), (ox + width - 4, wall_top)],
    )
    pygame.draw.polygon(
        surf,
        (200, 58, 48),
        [(ox + 10, wall_top - 2), (peak_x, peak_y + 5), (ox + width - 10, wall_top - 2)],
    )
    for tile_y in range(wall_top - 10, wall_top + 2, 4):
        pygame.draw.line(surf, (130, 32, 28), (ox + 12, tile_y), (ox + width - 12, tile_y), 1)

    ch_x = ox + width - 28
    pygame.draw.rect(surf, (140, 130, 120), (ch_x, wall_top - 18, 12, 22))
    pygame.draw.rect(surf, (100, 92, 86), (ch_x, wall_top - 18, 12, 22), 1)
    for dx, dy, r, alpha in ((2, -6, 5, 45), (8, -12, 7, 32)):
        puff = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(puff, (210, 215, 225, alpha), (r, r), r)
        surf.blit(puff, (ch_x + 4 + dx - r, wall_top - 20 + dy - r))

    _draw_window(surf, pygame.Rect(ox + 16, wall_top + 14, 18, 16), is_night, (160, 200, 255))

    door_x = ox + width // 2 - 4
    pygame.draw.rect(surf, (92, 62, 42), (door_x, wall_bottom - 22, 16, 22))
    pygame.draw.rect(surf, (60, 42, 30), (door_x, wall_bottom - 22, 16, 22), 1)
    pygame.draw.circle(surf, (220, 190, 80), (door_x + 12, wall_bottom - 12), 2)

    pygame.draw.rect(surf, (250, 245, 235), (ox + 5, wall_top - 2, width - 10, 4))

    return _scale_surface(surf, scale)


def _draw_npc_cottage_base(
    width: int,
    height: int,
    wall_color: Color,
    roof_dark: Color,
    roof_light: Color,
    trim_color: Color,
    door_color: Color,
    window_tint: Color,
    is_night: bool,
    *,
    flat_roof: bool = False,
    porch: bool = False,
    tool_shed: bool = False,
    antenna: bool = False,
    log_walls: bool = False,
) -> pygame.Surface:
    pad_bottom = 12
    total_h = height + pad_bottom
    surf = pygame.Surface((width + 20, total_h), pygame.SRCALPHA)
    ox, oy = 10, 0
    _draw_ground_shadow(surf, width, total_h - 4, alpha=70, spread=12)

    wall_top = oy + 28
    wall_bottom = oy + height - 4
    wall_rect = pygame.Rect(ox + 6, wall_top, width - 12, wall_bottom - wall_top)

    if log_walls:
        for row in range(wall_rect.height):
            t = row / max(1, wall_rect.height - 1)
            base = _lerp_color((120, 88, 58), (88, 62, 40), t)
            pygame.draw.line(
                surf,
                base,
                (wall_rect.left, wall_rect.top + row),
                (wall_rect.right, wall_rect.top + row),
            )
    else:
        _shaded_wall_gradient(surf, wall_rect, wall_color)

    peak_x = ox + width // 2
    if flat_roof:
        pygame.draw.rect(surf, roof_dark, (ox + 4, wall_top - 10, width - 8, 14), border_radius=2)
        pygame.draw.rect(surf, roof_light, (ox + 8, wall_top - 8, width - 16, 8))
    else:
        peak_y = oy + 10
        pygame.draw.polygon(surf, roof_dark, [(ox + 4, wall_top), (peak_x, peak_y), (ox + width - 4, wall_top)])
        pygame.draw.polygon(
            surf,
            roof_light,
            [(ox + 10, wall_top - 2), (peak_x, peak_y + 4), (ox + width - 10, wall_top - 2)],
        )

    pygame.draw.rect(surf, trim_color, (ox + 5, wall_top - 2, width - 10, 4))
    _draw_window(surf, pygame.Rect(ox + 14, wall_top + 12, 16, 14), is_night, window_tint)
    if width > 90:
        _draw_window(surf, pygame.Rect(ox + width - 32, wall_top + 12, 16, 14), is_night, window_tint)

    door_x = ox + width // 2 - 8
    pygame.draw.rect(surf, door_color, (door_x, wall_bottom - 22, 16, 22))
    pygame.draw.rect(surf, (40, 32, 28), (door_x, wall_bottom - 22, 16, 22), 1)

    if porch:
        pygame.draw.rect(surf, (100, 72, 48), (door_x - 10, wall_bottom - 8, 36, 6))
        pygame.draw.line(surf, (90, 64, 42), (door_x - 8, wall_bottom - 8), (door_x - 8, wall_bottom - 26), 2)
        pygame.draw.line(surf, (90, 64, 42), (door_x + 26, wall_bottom - 8), (door_x + 26, wall_bottom - 26), 2)

    if tool_shed:
        pygame.draw.rect(surf, (140, 100, 60), (ox + width - 28, wall_bottom - 18, 22, 16))
        pygame.draw.rect(surf, (90, 64, 40), (ox + width - 28, wall_bottom - 18, 22, 16), 1)
        pygame.draw.rect(surf, (180, 180, 190), (ox + width - 24, wall_bottom - 14, 6, 8))

    if antenna:
        ax = ox + width - 20
        pygame.draw.line(surf, (120, 130, 145), (ax, wall_top - 8), (ax, oy + 2), 2)
        pygame.draw.circle(surf, (220, 80, 80), (ax, oy + 2), 3)

    return surf


def draw_home_bob(
    x: int = 0,
    y: int = 0,
    scale: float = 1.0,
    width: int = 115,
    height: int = 78,
    is_night: bool = False,
) -> pygame.Surface:
    """Bob's workshop home — orange roof, tool shed."""
    surf = _draw_npc_cottage_base(
        width,
        height,
        (200, 175, 145),
        (160, 90, 40),
        (210, 130, 55),
        (240, 220, 180),
        (110, 72, 48),
        (255, 200, 120),
        is_night,
        tool_shed=True,
    )
    return _scale_surface(surf, scale)


def draw_home_chen(
    x: int = 0,
    y: int = 0,
    scale: float = 1.0,
    width: int = 115,
    height: int = 78,
    is_night: bool = False,
) -> pygame.Surface:
    """Dr. Chen — pale walls, blue trim, antenna."""
    surf = _draw_npc_cottage_base(
        width,
        height,
        (232, 238, 248),
        (70, 110, 180),
        (100, 150, 220),
        (180, 210, 240),
        (140, 160, 190),
        (120, 180, 255),
        is_night,
        antenna=True,
    )
    return _scale_surface(surf, scale)


def draw_home_maria(
    x: int = 0,
    y: int = 0,
    scale: float = 1.0,
    width: int = 115,
    height: int = 78,
    is_night: bool = False,
) -> pygame.Surface:
    """Maria's flat — modern flat roof, rose accent."""
    surf = _draw_npc_cottage_base(
        width,
        height,
        (218, 208, 214),
        (150, 130, 145),
        (190, 170, 185),
        (255, 200, 210),
        (120, 90, 110),
        (255, 180, 200),
        is_night,
        flat_roof=True,
    )
    return _scale_surface(surf, scale)


def draw_home_jenkins(
    x: int = 0,
    y: int = 0,
    scale: float = 1.0,
    width: int = 115,
    height: int = 78,
    is_night: bool = False,
) -> pygame.Surface:
    """Jenkins cabin — dark logs, green roof, porch."""
    surf = _draw_npc_cottage_base(
        width,
        height,
        (130, 100, 72),
        (58, 88, 52),
        (82, 118, 68),
        (180, 160, 120),
        (72, 52, 36),
        (180, 210, 160),
        is_night,
        log_walls=True,
        porch=True,
    )
    return _scale_surface(surf, scale)
