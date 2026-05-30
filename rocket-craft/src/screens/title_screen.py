"""Animated title screen with parallax stars and menu buttons."""

from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple

import pygame

from config import SCREEN_HEIGHT, SCREEN_WIDTH
from core.game_session import GameSession
from core.save_load import SaveManager
from graphics.ui import get_font

try:
    from audio.audio_manager import AudioManager
except ImportError:
    AudioManager = None  # type: ignore[misc, assignment]


Color = Tuple[int, int, int]


class MenuButton:
    def __init__(self, label: str, center: Tuple[int, int], action: str) -> None:
        self.label = label
        self.action = action
        self.base_rect = pygame.Rect(0, 0, 240, 50)
        self.base_rect.center = center
        self.press_timer = 0.0

    def update(self, dt: float) -> None:
        self.press_timer = max(0.0, self.press_timer - dt)

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> Optional[str]:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.base_rect.collidepoint(mouse_pos):
                self.press_timer = 0.1
                return self.action
        return None

    def draw(self, screen: pygame.Surface, font: pygame.font.Font, mouse_pos: Tuple[int, int]) -> None:
        hovered = self.base_rect.collidepoint(mouse_pos)
        scale = 0.95 if self.press_timer > 0.0 else 1.0
        width = int(self.base_rect.width * scale)
        height = int(self.base_rect.height * scale)
        rect = pygame.Rect(0, 0, width, height)
        rect.center = self.base_rect.center

        bg = (58, 64, 82) if hovered else (32, 37, 52)
        border = (120, 132, 160) if hovered else (74, 84, 112)
        text_color = (255, 236, 39) if hovered else (255, 255, 255)

        pygame.draw.rect(screen, bg, rect, border_radius=4)
        pygame.draw.rect(screen, border, rect, 2, border_radius=4)
        label = font.render(self.label, True, text_color)
        screen.blit(label, label.get_rect(center=rect.center))


class TitleScreen:
    """Start screen; returns action strings from ``handle_event``."""

    def __init__(
        self,
        save_manager: SaveManager,
        audio: "AudioManager | None" = None,
        session: Optional[GameSession] = None,
    ) -> None:
        self.save_manager = save_manager
        self.audio = audio
        self.session = session
        self.font_logo = get_font(76, bold=True)
        self.font_button = get_font(24, bold=True)
        self.font_small = get_font(15)
        self.time = 0.0
        self.notice = ""

        start_y = 355
        self.buttons = [
            MenuButton("NEW GAME", (SCREEN_WIDTH // 2, start_y), "new_game"),
            MenuButton("LOAD GAME", (SCREEN_WIDTH // 2, start_y + 64), "load_game"),
            MenuButton("SETTINGS", (SCREEN_WIDTH // 2, start_y + 128), "settings"),
            MenuButton("QUIT", (SCREEN_WIDTH // 2, start_y + 192), "quit"),
        ]

        rng = random.Random(42)
        self.star_layers: List[Tuple[float, List[Tuple[int, int, int]]]] = []
        for speed, count, size_max in ((8.0, 60, 1), (18.0, 45, 2), (32.0, 28, 3)):
            stars = [
                (
                    rng.randrange(0, SCREEN_WIDTH),
                    rng.randrange(0, SCREEN_HEIGHT),
                    rng.randrange(1, size_max + 1),
                )
                for _ in range(count)
            ]
            self.star_layers.append((speed, stars))

    def update(self, dt: float) -> None:
        self.time += dt
        for button in self.buttons:
            button.update(dt)

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        mouse_pos = pygame.mouse.get_pos()
        for button in self.buttons:
            action = button.handle_event(event, mouse_pos)
            if action == "load_game":
                if self.audio is not None:
                    self.audio.play_sfx("click")
                return "load_screen"
            if action in ("new_game", "quit") and self.audio is not None:
                self.audio.play_sfx("click")
            if action == "settings":
                self.notice = "Settings are coming soon."
                print("Settings placeholder")
                return None
            if action:
                return action

        return None

    def draw(self, screen: pygame.Surface) -> None:
        self._draw_background(screen)
        self._draw_logo(screen)
        mouse_pos = pygame.mouse.get_pos()
        for button in self.buttons:
            button.draw(screen, self.font_button, mouse_pos)

        if self.notice:
            notice = self.font_small.render(self.notice, True, (180, 190, 210))
            screen.blit(notice, notice.get_rect(center=(SCREEN_WIDTH // 2, 610)))

        version = self.font_small.render("v0.1.0 - Early Access", True, (130, 140, 160))
        screen.blit(version, version.get_rect(bottomright=(SCREEN_WIDTH - 18, SCREEN_HEIGHT - 14)))

    def _draw_background(self, screen: pygame.Surface) -> None:
        screen.fill((8, 12, 28))
        for y in range(SCREEN_HEIGHT):
            t = y / max(1, SCREEN_HEIGHT - 1)
            color = (
                int(8 + 10 * t),
                int(12 + 18 * t),
                int(28 + 38 * t),
            )
            pygame.draw.line(screen, color, (0, y), (SCREEN_WIDTH, y))

        for speed, stars in self.star_layers:
            offset = (self.time * speed) % SCREEN_WIDTH
            alpha = min(255, int(120 + speed * 4))
            color = (alpha, alpha, min(255, alpha + 25))
            for x, y, radius in stars:
                sx = int((x - offset) % SCREEN_WIDTH)
                pygame.draw.circle(screen, color, (sx, y), radius)

    def _draw_logo(self, screen: pygame.Surface) -> None:
        bounce = math.sin(self.time * 2.0) * 8.0
        text = "ROCKETCRAFT"
        shadow = self.font_logo.render(text, True, (255, 196, 54))
        logo = self.font_logo.render(text, True, (255, 255, 255))
        center = (SCREEN_WIDTH // 2, int(180 + bounce))
        screen.blit(shadow, shadow.get_rect(center=(center[0] + 5, center[1] + 6)))
        screen.blit(logo, logo.get_rect(center=center))

        subtitle = self.font_small.render("A tiny town with orbital ambitions", True, (180, 190, 220))
        screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 246)))
