"""Pseudo-3D room rendering — thick/thin walls and layered furniture depth."""

from __future__ import annotations

from typing import List, Sequence, Tuple

import pygame

Color = Tuple[int, int, int]


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_color(c1: Color, c2: Color, t: float) -> Color:
    return (
        int(lerp(c1[0], c2[0], t)),
        int(lerp(c1[1], c2[1], t)),
        int(lerp(c1[2], c2[2], t)),
    )


def vertical_gradient_rect(surf: pygame.Surface, rect: pygame.Rect, top: Color, bottom: Color) -> None:
    if rect.height <= 0:
        return
    for row in range(rect.height):
        t = row / max(1, rect.height - 1)
        color = lerp_color(top, bottom, t)
        pygame.draw.line(surf, color, (rect.left, rect.top + row), (rect.right - 1, rect.top + row))


def draw_room_shell(
    screen: pygame.Surface,
    room: pygame.Rect,
    *,
    wall_back: Color = (248, 242, 232),
    wall_side_dark: Color = (210, 198, 182),
    wall_side_light: Color = (232, 224, 212),
    floor_near: Color = (118, 82, 52),
    floor_far: Color = (156, 108, 68),
) -> Tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
    """Draw back wall, side walls (thick strips), and perspective floor. Returns floor rect."""
    pygame.draw.rect(screen, (18, 20, 28), room.inflate(10, 10), border_radius=6)

    pad = 6
    inner = room.inflate(-pad * 2, -pad * 2)
    floor_top = inner.y + int(inner.height * 0.36)
    back = pygame.Rect(inner.x, inner.y, inner.width, floor_top - inner.y)

    vertical_gradient_rect(screen, back, wall_back, lerp_color(wall_back, (220, 210, 195), 0.55))
    pygame.draw.rect(screen, lerp_color(wall_back, (180, 168, 150), 0.25), back, 0)
    baseboard = pygame.Rect(back.x, back.bottom - 10, back.width, 10)
    pygame.draw.rect(screen, (92, 68, 48), baseboard)
    pygame.draw.line(screen, (120, 90, 62), (baseboard.left, baseboard.top), (baseboard.right, baseboard.top), 2)

    side_w = max(52, int(inner.width * 0.09))
    left_wall = pygame.Rect(inner.x, floor_top - 8, side_w, inner.bottom - floor_top + 16)
    right_wall = pygame.Rect(inner.right - side_w, floor_top - 8, side_w, inner.bottom - floor_top + 16)
    vertical_gradient_rect(screen, left_wall, wall_side_light, wall_side_dark)
    vertical_gradient_rect(screen, right_wall, wall_side_dark, lerp_color(wall_side_dark, (160, 148, 132), 0.4))
    pygame.draw.line(screen, (140, 128, 112), (left_wall.right, left_wall.top), (left_wall.right, left_wall.bottom), 3)
    pygame.draw.line(screen, (100, 92, 82), (right_wall.left, right_wall.top), (right_wall.left, right_wall.bottom), 3)

    floor = pygame.Rect(inner.x + side_w - 4, floor_top, inner.width - side_w * 2 + 8, inner.bottom - floor_top)
    for row in range(floor.height):
        t = row / max(1, floor.height - 1)
        color = lerp_color(floor_far, floor_near, t**0.85)
        pygame.draw.line(screen, color, (floor.left, floor.top + row), (floor.right, floor.top + row))
        if row % 28 < 2:
            pygame.draw.line(screen, lerp_color(color, (40, 28, 18), 0.35), (floor.left, floor.top + row), (floor.right, floor.top + row), 1)

    plank_x = floor.left + 8
    while plank_x < floor.right - 8:
        shade = lerp_color(floor_near, (70, 48, 30), 0.15 if (plank_x // 36) % 2 else 0.05)
        pygame.draw.line(screen, shade, (plank_x, floor.top + 4), (plank_x, floor.bottom - 4), 1)
        plank_x += 36

    ceiling_shadow = pygame.Surface((inner.width, 28), pygame.SRCALPHA)
    for row in range(28):
        alpha = int(55 * (1.0 - row / 28))
        pygame.draw.line(ceiling_shadow, (0, 0, 0, alpha), (0, row), (inner.width, row))
    screen.blit(ceiling_shadow, (inner.x, inner.y))

    return floor, left_wall, right_wall


def draw_recessed_window(
    screen: pygame.Surface,
    wall_rect: pygame.Rect,
    offset: Tuple[int, int],
    size: Tuple[int, int],
    is_night: bool = False,
) -> None:
    wx = wall_rect.x + offset[0]
    wy = wall_rect.y + offset[1]
    outer = pygame.Rect(wx - 8, wy - 6, size[0] + 16, size[1] + 14)
    recess = pygame.Rect(wx - 4, wy - 2, size[0] + 8, size[1] + 8)
    pygame.draw.rect(screen, (72, 78, 92), outer, border_radius=2)
    pygame.draw.rect(screen, (48, 52, 64), recess)
    win = pygame.Rect(wx, wy, size[0], size[1])
    sky_top = (40, 70, 130) if is_night else (120, 180, 255)
    sky_bot = (20, 35, 70) if is_night else (80, 140, 220)
    vertical_gradient_rect(screen, win, sky_top, sky_bot)
    pygame.draw.rect(screen, (220, 228, 240), win, 2, border_radius=1)
    pygame.draw.line(screen, (245, 250, 255), (win.centerx, win.top + 2), (win.centerx, win.bottom - 2), 2)
    pygame.draw.line(screen, (245, 250, 255), (win.left + 2, win.centery), (win.right - 2, win.centery), 2)
    sill = pygame.Rect(win.x - 6, win.bottom, win.width + 12, 6)
    pygame.draw.rect(screen, (180, 170, 155), sill, border_radius=1)
    pygame.draw.rect(screen, (120, 110, 98), sill, 1, border_radius=1)


def draw_box_3d(
    screen: pygame.Surface,
    rect: pygame.Rect,
    top: Color,
    front: Color,
    side: Color,
    depth: int = 10,
) -> None:
    """Draw furniture/cabinet with top face and thick front/side."""
    top_rect = pygame.Rect(rect.x, rect.y - depth, rect.width, depth + 4)
    side_rect = pygame.Rect(rect.right - depth, rect.y, depth, rect.height)
    pygame.draw.rect(screen, side, side_rect)
    pygame.draw.rect(screen, front, rect)
    pygame.draw.polygon(
        screen,
        top,
        [
            (rect.x, rect.y),
            (rect.right, rect.y),
            (rect.right - depth, rect.y - depth),
            (rect.x + depth, rect.y - depth),
        ],
    )
    pygame.draw.rect(screen, lerp_color(front, (20, 18, 16), 0.5), rect, 1)
    shadow = pygame.Surface((rect.width + depth + 8, depth + 6), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 50), shadow.get_rect())
    screen.blit(shadow, (rect.x + 4, rect.bottom - 2))


def draw_bed_3d(
    screen: pygame.Surface,
    rect: pygame.Rect,
    blanket: Color,
    wood: Color = (101, 67, 33),
) -> None:
    depth = 14
    frame = rect.inflate(0, 6)
    draw_box_3d(screen, frame, lerp_color(wood, (140, 100, 60), 0.3), wood, lerp_color(wood, (60, 40, 24), 0.35), depth=depth)
    mattress = pygame.Rect(frame.x + 4, frame.y + 6, frame.width - 8, 28)
    pygame.draw.rect(screen, (248, 248, 252), mattress, border_radius=3)
    pygame.draw.rect(screen, (220, 222, 230), mattress, 1, border_radius=3)
    pillow = pygame.Rect(mattress.x + 6, mattress.y + 4, 26, 16)
    pygame.draw.ellipse(screen, (255, 255, 255), pillow)
    pygame.draw.ellipse(screen, (230, 232, 240), pillow, 1)
    blanket_rect = pygame.Rect(frame.x + 2, frame.y + 30, frame.width - 4, frame.height - 32)
    pygame.draw.rect(screen, blanket, blanket_rect, border_radius=4)
    pygame.draw.rect(screen, lerp_color(blanket, (255, 255, 255), 0.2), blanket_rect, 1, border_radius=4)
    fold = blanket_rect.x + blanket_rect.width // 3
    pygame.draw.line(screen, lerp_color(blanket, (0, 0, 0), 0.15), (fold, blanket_rect.top), (fold, blanket_rect.bottom), 2)


def draw_table_lamp_3d(screen: pygame.Surface, x: int, y: int) -> None:
    top = pygame.Rect(x, y, 48, 10)
    leg = pygame.Rect(x + 20, y + 10, 8, 34)
    base = pygame.Rect(x + 10, y + 42, 28, 8)
    draw_box_3d(screen, top, (255, 248, 220), (240, 230, 200), (200, 185, 150), depth=6)
    pygame.draw.rect(screen, (90, 92, 100), leg)
    pygame.draw.rect(screen, (70, 72, 80), base, border_radius=2)
    pygame.draw.polygon(
        screen,
        (255, 242, 190),
        [(x + 6, y + 8), (x + 42, y + 8), (x + 24, y - 22)],
    )
    glow = pygame.Surface((64, 64), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 230, 150, 70), (32, 32), 26)
    screen.blit(glow, (x - 8, y - 30))


def draw_bookshelf_3d(screen: pygame.Surface, rect: pygame.Rect) -> None:
    draw_box_3d(
        screen,
        rect,
        lerp_color((120, 85, 55), (150, 110, 72), 0.4),
        (100, 70, 45),
        (72, 50, 32),
        depth=16,
    )
    for row in range(4):
        y = rect.y + 18 + row * 32
        pygame.draw.line(screen, (62, 44, 28), (rect.x + 4, y), (rect.right - 20, y), 3)
        for i, color in enumerate(((180, 60, 60), (60, 100, 180), (80, 160, 80), (200, 160, 60))):
            book = pygame.Rect(rect.x + 10 + i * 18, y - 20, 14, 22)
            pygame.draw.rect(screen, color, book, border_radius=1)
            pygame.draw.rect(screen, lerp_color(color, (0, 0, 0), 0.25), book, 1, border_radius=1)


def draw_door_3d(screen: pygame.Surface, room: pygame.Rect, door: pygame.Rect) -> None:
    door_screen = pygame.Rect(room.x + door.x, room.y + door.y, door.width, door.height)
    frame = door_screen.inflate(16, 10)
    pygame.draw.rect(screen, (62, 44, 30), frame, border_radius=3)
    pygame.draw.rect(screen, (48, 34, 24), frame, 3, border_radius=3)
    draw_box_3d(
        screen,
        door_screen,
        lerp_color((110, 78, 52), (130, 95, 65), 0.3),
        (92, 62, 42),
        (68, 46, 30),
        depth=8,
    )
    knob = (door_screen.right - 14, door_screen.centery)
    pygame.draw.circle(screen, (220, 190, 80), knob, 4)
    pygame.draw.circle(screen, (160, 130, 50), knob, 4, 1)
