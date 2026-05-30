"""Save-slot selector screen."""

from __future__ import annotations

from typing import List, Optional

import pygame

from config import SCREEN_HEIGHT, SCREEN_WIDTH
from core.save_load import SaveManager
from graphics.ui import get_font

try:
    from audio.audio_manager import AudioManager
except ImportError:
    AudioManager = None  # type: ignore[misc, assignment]


class LoadGameScreen:
    def __init__(self, save_manager: SaveManager, audio: "AudioManager | None" = None) -> None:
        self.save_manager = save_manager
        self.audio = audio
        self.font_title = get_font(40, bold=True)
        self.font = get_font(20)
        self.font_small = get_font(15)
        self.saves: List[dict] = []
        self.selected: Optional[int] = None
        self.back_rect = pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 86, 200, 50)
        self.refresh()

    def refresh(self) -> None:
        self.saves = self.save_manager.get_saves()[:5]
        self.selected = None

    def update(self, dt: float) -> None:
        self.selected = self._slot_at(pygame.mouse.get_pos())

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "title"
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None

        if self.back_rect.collidepoint(event.pos):
            if self.audio:
                self.audio.play_sfx("click")
            return "title"

        index = self._slot_at(event.pos)
        if index is not None and index < len(self.saves):
            if self.audio:
                self.audio.play_sfx("confirm")
            return f"load_game:{self.saves[index]['filename']}"
        if self.audio:
            self.audio.play_sfx("error")
        return None

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((20, 20, 40))
        title = self.font_title.render("LOAD GAME", True, (255, 255, 255))
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 68)))

        if not self.saves:
            msg = self.font.render("No saves found. Start a New Game first.", True, (180, 190, 210))
            screen.blit(msg, msg.get_rect(center=(SCREEN_WIDTH // 2, 126)))

        for i in range(5):
            self._draw_slot(screen, i)

        pygame.draw.rect(screen, (80, 80, 80), self.back_rect, border_radius=8)
        pygame.draw.rect(screen, (140, 140, 160), self.back_rect, 2, border_radius=8)
        back_text = self.font.render("BACK", True, (255, 255, 255))
        screen.blit(back_text, back_text.get_rect(center=self.back_rect.center))

    def _slot_rect(self, index: int) -> pygame.Rect:
        return pygame.Rect(SCREEN_WIDTH // 2 - 250, 150 + index * 90, 500, 80)

    def _slot_at(self, pos: tuple) -> Optional[int]:
        for i in range(5):
            if self._slot_rect(i).collidepoint(pos):
                return i
        return None

    def _draw_slot(self, screen: pygame.Surface, index: int) -> None:
        rect = self._slot_rect(index)
        color = (60, 60, 100) if index == self.selected else (40, 40, 70)
        pygame.draw.rect(screen, color, rect, border_radius=8)
        pygame.draw.rect(screen, (100, 100, 150), rect, 2, border_radius=8)

        if index >= len(self.saves):
            empty = self.font.render("--- Empty ---", True, (100, 100, 100))
            screen.blit(empty, empty.get_rect(center=rect.center))
            return

        save = self.saves[index]
        name_text = self.font.render(str(save.get("player_name", "Director")), True, (255, 255, 255))
        day_text = self.font_small.render(f"Day {save.get('day', 1)}", True, (200, 200, 200))
        money_text = self.font.render(f"${int(save.get('money', 0)):,}", True, (100, 255, 100))
        date = str(save.get("date", ""))
        date_text = self.font_small.render(date[:10] if date else "Unknown date", True, (150, 150, 150))

        screen.blit(name_text, (rect.x + 20, rect.y + 10))
        screen.blit(day_text, (rect.x + 20, rect.y + 42))
        screen.blit(money_text, (rect.x + 300, rect.y + 10))
        screen.blit(date_text, (rect.x + 300, rect.y + 42))
