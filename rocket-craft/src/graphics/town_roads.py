"""Layered town roads with curbs, asphalt texture, and lane markings."""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

import pygame

Point = Tuple[float, float]


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_color(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    return (
        int(_lerp(c1[0], c2[0], t)),
        int(_lerp(c1[1], c2[1], t)),
        int(_lerp(c1[2], c2[2], t)),
    )


def _offset_polyline(points: Sequence[Point], width: float, side: float) -> List[Tuple[int, int]]:
    """Offset polyline to one side for road ribbon mesh."""
    if len(points) < 2:
        return []
    out: List[Tuple[int, int]] = []
    half = width * 0.5 * side
    for i, (x, y) in enumerate(points):
        if i == 0:
            x0, y0 = points[0]
            x1, y1 = points[1]
        elif i == len(points) - 1:
            x0, y0 = points[-2]
            x1, y1 = points[-1]
        else:
            x0, y0 = points[i - 1]
            x1, y1 = points[i + 1]
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length * half, dx / length * half
        out.append((int(x + nx), int(y + ny)))
    return out


def _ribbon_polygon(points: Sequence[Point], width: float) -> List[Tuple[int, int]]:
    left = _offset_polyline(points, width, 1.0)
    right = _offset_polyline(points, width, -1.0)
    return left + list(reversed(right))


def _polygon_bounds(points: Sequence[Tuple[int, int]]) -> pygame.Rect:
    if not points:
        return pygame.Rect(0, 0, 0, 0)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)


class TownRoadRenderer:
    """Draw road network with depth: curb shadow, asphalt, wear, center line."""

    def __init__(self) -> None:
        self._dash_phase = 0.0

    def update(self, dt: float) -> None:
        self._dash_phase = (self._dash_phase + dt * 0.35) % 1.0

    def draw_network(
        self,
        screen: pygame.Surface,
        world_to_screen,
        routes: Sequence[Sequence[Point]],
        light: float = 1.0,
    ) -> None:
        night = 1.0 - light
        curb = _lerp_color((58, 54, 48), (42, 40, 38), night)
        curb_hi = _lerp_color((108, 102, 94), (72, 68, 62), night)
        asphalt = _lerp_color((88, 86, 82), (52, 54, 58), night)
        asphalt_hi = _lerp_color((112, 110, 104), (68, 70, 74), night)
        line_color = _lerp_color((240, 228, 160), (180, 170, 120), night)

        for route in routes:
            if len(route) < 2:
                continue
            screen_pts = [world_to_screen(x, y) for x, y in route]
            self._draw_road_segment(
                screen,
                screen_pts,
                curb,
                curb_hi,
                asphalt,
                asphalt_hi,
                line_color,
                width=44,
                light=light,
            )

        for route in routes:
            if len(route) < 2:
                continue
            pts = [world_to_screen(x, y) for x, y in route]
            self._draw_intersection_patch(screen, pts[0], asphalt_hi, 26, light)
            self._draw_intersection_patch(screen, pts[-1], asphalt_hi, 26, light)

    def _draw_intersection_patch(
        self,
        screen: pygame.Surface,
        center: Tuple[int, int],
        color: Tuple[int, int, int],
        radius: int,
        light: float,
    ) -> None:
        patch = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(patch, (*color, int(200 * light + 40)), (patch.get_width() // 2, patch.get_height() // 2), radius)
        pygame.draw.circle(patch, (255, 255, 255, 35), (patch.get_width() // 2, patch.get_height() // 2), radius, 2)
        screen.blit(patch, (center[0] - patch.get_width() // 2, center[1] - patch.get_height() // 2))

    def _draw_road_segment(
        self,
        screen: pygame.Surface,
        points: Sequence[Tuple[int, int]],
        curb: Tuple[int, int, int],
        curb_hi: Tuple[int, int, int],
        asphalt: Tuple[int, int, int],
        asphalt_hi: Tuple[int, int, int],
        line_color: Tuple[int, int, int],
        width: int,
        light: float,
    ) -> None:
        if len(points) < 2:
            return

        float_pts: List[Point] = [(float(x), float(y)) for x, y in points]

        shadow_w = width + 14
        shadow_poly = _ribbon_polygon(float_pts, shadow_w)
        if len(shadow_poly) >= 3:
            shadow_surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            pygame.draw.polygon(shadow_surf, (0, 0, 0, 45), shadow_poly)
            screen.blit(shadow_surf, (0, 0))

        curb_poly = _ribbon_polygon(float_pts, width + 10)
        if len(curb_poly) >= 3:
            pygame.draw.polygon(screen, curb, curb_poly)
            pygame.draw.polygon(screen, curb_hi, curb_poly, 2)

        road_poly = _ribbon_polygon(float_pts, width)
        if len(road_poly) >= 3:
            pygame.draw.polygon(screen, asphalt, road_poly)
            self._texture_fill(screen, road_poly, asphalt, asphalt_hi, light)

        inner_poly = _ribbon_polygon(float_pts, max(8, width - 16))
        if len(inner_poly) >= 3:
            pygame.draw.polygon(screen, asphalt_hi, inner_poly, 1)

        self._center_dashes(screen, points, line_color, width)

    def _texture_fill(
        self,
        screen: pygame.Surface,
        polygon: List[Tuple[int, int]],
        base: Tuple[int, int, int],
        highlight: Tuple[int, int, int],
        light: float,
    ) -> None:
        bounds = _polygon_bounds(polygon).clip(screen.get_rect())
        if bounds.width <= 0 or bounds.height <= 0:
            return
        for y in range(bounds.top, bounds.bottom, 5):
            t = (y - bounds.top) / max(1, bounds.height)
            shade = _lerp_color(base, highlight, (t * 0.35 + (y % 10) / 22.0) * light)
            x = bounds.left + int((y % 7) * 1.4)
            pygame.draw.line(screen, shade, (x, y), (bounds.right, y), 1)

    def _center_dashes(
        self,
        screen: pygame.Surface,
        points: Sequence[Tuple[int, int]],
        color: Tuple[int, int, int],
        road_width: int,
    ) -> None:
        dash_len = 18
        gap_len = 14
        pattern = dash_len + gap_len
        traveled = self._dash_phase * pattern

        for i in range(len(points) - 1):
            x0, y0 = points[i]
            x1, y1 = points[i + 1]
            seg_len = math.hypot(x1 - x0, y1 - y0)
            if seg_len < 1:
                continue
            ux, uy = (x1 - x0) / seg_len, (y1 - y0) / seg_len
            dist = 0.0
            while dist < seg_len:
                phase = (traveled + dist) % pattern
                if phase < dash_len:
                    start = dist
                    end = min(seg_len, dist + dash_len - phase)
                    sx = int(x0 + ux * start)
                    sy = int(y0 + uy * start)
                    ex = int(x0 + ux * end)
                    ey = int(y0 + uy * end)
                    pygame.draw.line(screen, color, (sx, sy), (ex, ey), 2)
                dist += pattern - ((traveled + dist) % pattern) if (traveled + dist) % pattern else pattern
