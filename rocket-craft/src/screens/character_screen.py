"""Simple character creation screen."""

from __future__ import annotations

from typing import List, Optional, Tuple

import pygame

from config import SCREEN_HEIGHT, SCREEN_WIDTH
from core.game_session import GameSession
from graphics.text_input import TextInput
from graphics.ui import get_font

Color = Tuple[int, int, int]


class CharacterScreen:
    def __init__(self, session: GameSession, audio=None) -> None:
        self.session = session
        self.audio = audio
        self.font_title = get_font(42, bold=True)
        self.font = get_font(22)
        self.font_small = get_font(16)
        self.name = session.player_name if session.player_name != "Director" else ""
        self.name_input = TextInput(
            self.font,
            SCREEN_WIDTH // 2 - 90,
            332,
            270,
            max_length=20,
            placeholder="Director",
        )
        self.name_input.set_text(self.name)
        self.colors: List[Color] = [(255, 236, 39), (80, 180, 255), (255, 110, 150), (120, 220, 120)]
        self.color_index = 0
        self.start_rect = pygame.Rect(SCREEN_WIDTH // 2 - 130, 520, 260, 54)
        self.back_rect = pygame.Rect(SCREEN_WIDTH // 2 - 130, 586, 260, 44)

    def update(self, dt: float) -> None:
        self.name_input.update(dt)

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        completed = self.name_input.handle_event(event)
        if completed:
            self.name = completed
            self._commit()
            return "new_game_ready"

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "title"
            if event.key == pygame.K_RETURN:
                self._commit()
                return "new_game_ready"
            if event.key in (pygame.K_LEFT, pygame.K_a) and not self.name_input.active:
                self.color_index = (self.color_index - 1) % len(self.colors)
            elif event.key in (pygame.K_RIGHT, pygame.K_d) and not self.name_input.active:
                self.color_index = (self.color_index + 1) % len(self.colors)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.start_rect.collidepoint(event.pos):
                self._commit()
                return "new_game_ready"
            if self.back_rect.collidepoint(event.pos):
                return "title"
            for i, rect in enumerate(self._color_rects()):
                if rect.collidepoint(event.pos):
                    self.color_index = i
                    if self.audio:
                        self.audio.play_sfx("click")
        return None

    def _commit(self) -> None:
        self.name = self.name_input.get_text()
        self.session.player_name = (self.name.strip() or "Director")[:20]
        self.session.player_color = self.colors[self.color_index]
        if self.audio:
            self.audio.play_sfx("confirm")

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((12, 16, 30))
        title = self.font_title.render("CREATE DIRECTOR", True, (255, 236, 39))
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 110)))

        preview_x, preview_y = SCREEN_WIDTH // 2, 260
        pygame.draw.circle(screen, (20, 24, 32), (preview_x, preview_y), 42)
        color = self.colors[self.color_index]
        pygame.draw.polygon(screen, color, [(preview_x, preview_y - 42), (preview_x - 34, preview_y + 32), (preview_x + 34, preview_y + 32)])

        label = self.font.render("Name", True, (220, 230, 245))
        screen.blit(label, (SCREEN_WIDTH // 2 - 180, 340))
        self.name_input.render(screen)

        color_label = self.font.render("Suit Color", True, (220, 230, 245))
        screen.blit(color_label, (SCREEN_WIDTH // 2 - 180, 410))
        for i, rect in enumerate(self._color_rects()):
            pygame.draw.rect(screen, self.colors[i], rect, border_radius=5)
            pygame.draw.rect(screen, (255, 255, 255) if i == self.color_index else (50, 58, 76), rect, 3 if i == self.color_index else 1, border_radius=5)

        self._button(screen, self.start_rect, "START")
        self._button(screen, self.back_rect, "BACK")
        hint = self.font_small.render("Type a name. Use Left/Right or click swatches.", True, (150, 164, 190))
        screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, 665)))

    def _color_rects(self) -> List[pygame.Rect]:
        start_x = SCREEN_WIDTH // 2 - 90
        return [pygame.Rect(start_x + i * 56, 404, 42, 42) for i in range(len(self.colors))]

    def _button(self, screen: pygame.Surface, rect: pygame.Rect, text: str) -> None:
        hover = rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, (58, 64, 82) if hover else (32, 37, 52), rect, border_radius=5)
        pygame.draw.rect(screen, (120, 132, 160), rect, 2, border_radius=5)
        surf = self.font.render(text, True, (255, 236, 39) if hover else (255, 255, 255))
        screen.blit(surf, surf.get_rect(center=rect.center))
