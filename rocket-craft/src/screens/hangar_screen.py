"""Rocket assembly hangar with catalog, budget, and launch countdown."""

from __future__ import annotations

from typing import List, Optional, Tuple

import pygame

from config import SCREEN_HEIGHT, SCREEN_WIDTH
from core.fonts import get_game_font
from core.game_session import GameSession
from entities.parts import PARTS_CATALOG, is_launchable, total_cost, total_mass
from systems.story_events import StoryEventManager, StoryEventUI

try:
    from audio.audio_manager import AudioManager
except ImportError:
    AudioManager = None  # type: ignore[misc, assignment]


class HangarScreen:
    def __init__(
        self,
        session: GameSession,
        audio: "AudioManager | None" = None,
        story_manager: Optional[StoryEventManager] = None,
    ) -> None:
        self.session = session
        self.audio = audio
        self.story_manager = story_manager or StoryEventManager(session)
        self.story_ui = StoryEventUI(self.story_manager)
        self.font = get_game_font(18)
        self.font_title = get_game_font(26, bold=True)
        self.font_small = get_game_font(15)
        self.catalog_keys = [k for k in PARTS_CATALOG if k in session.unlocked_parts]
        self.selected_catalog = 0
        self.scroll = 0
        self.countdown = 0.0
        self.pending_launch = False
        self.notice = ""
        self.notice_timer = 0.0
        self.launch_rect = pygame.Rect(SCREEN_WIDTH - 250, SCREEN_HEIGHT - 90, 220, 56)
        self._story_checked = False

    def on_enter(self) -> None:
        self._story_checked = False

    def is_launchable(self) -> bool:
        return is_launchable(self.session.rocket_part_keys)

    def add_part(self, part_key: str) -> bool:
        part = PARTS_CATALOG.get(part_key)
        if part is None:
            return False
        if self.session.money < part.cost:
            self.notice = "Not enough funds."
            self.notice_timer = 2.0
            if self.audio:
                self.audio.play_sfx("error")
            return False
        self.session.money -= part.cost
        self.session.rocket_part_keys.append(part_key)
        self.notice = f"Added {part.name}"
        self.notice_timer = 2.0
        if self.audio:
            self.audio.play_sfx("confirm")
        return True

    def remove_last_part(self) -> None:
        if self.session.rocket_part_keys:
            self.session.rocket_part_keys.pop()
            self.notice = "Removed last part"
            self.notice_timer = 1.5

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if self.story_ui.active:
            self.story_ui.handle_event(event)
            return None

        if self.countdown > 0:
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "town"
            if event.key == pygame.K_UP:
                self.selected_catalog = max(0, self.selected_catalog - 1)
            elif event.key == pygame.K_DOWN:
                self.selected_catalog = min(len(self.catalog_keys) - 1, self.selected_catalog + 1)
            elif event.key == pygame.K_RETURN:
                if 0 <= self.selected_catalog < len(self.catalog_keys):
                    self.add_part(self.catalog_keys[self.selected_catalog])
            elif event.key == pygame.K_BACKSPACE:
                self.remove_last_part()
            elif event.key == pygame.K_l and self.is_launchable():
                self._start_countdown()

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None

        mouse = event.pos
        if self.launch_rect.collidepoint(mouse) and self.is_launchable():
            self._start_countdown()
            return None

        list_rect = pygame.Rect(24, 100, 320, SCREEN_HEIGHT - 200)
        if list_rect.collidepoint(mouse):
            rel_y = mouse[1] - list_rect.y + self.scroll
            index = rel_y // 34
            if 0 <= index < len(self.catalog_keys):
                self.selected_catalog = index
                self.add_part(self.catalog_keys[index])
        return None

    def _start_countdown(self) -> None:
        self.countdown = 10.0
        self.notice = "Preparing launch."
        self.notice_timer = 2.0
        if self.audio:
            self.audio.play_sfx("confirm")

    def update(self, dt: float) -> None:
        if not self._story_checked:
            self._story_checked = True
            self.story_ui.try_open("hangar")
        if self.story_ui.active:
            return

        if self.notice_timer > 0:
            self.notice_timer -= dt

        if self.countdown > 0:
            self.countdown -= dt
            if self.countdown <= 0:
                self.pending_launch = True

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((28, 32, 42))
        title = self.font_title.render("Rocket Hangar", True, (255, 236, 39))
        screen.blit(title, (28, 22))

        money = self.font.render(f"Funds: ${self.session.money:,}", True, (255, 236, 39))
        screen.blit(money, (28, 58))

        self._draw_catalog(screen)
        self._draw_assembled_rocket(screen)
        self._draw_stats(screen)

        launchable = self.is_launchable()
        color = (50, 180, 80) if launchable else (90, 90, 90)
        if self.countdown > 0:
            color = (220, 140, 40)
            label = f"Launch in {int(self.countdown + 0.99)}..."
        elif launchable:
            label = "Launch Rocket"
        else:
            label = "Missing Parts"

        pygame.draw.rect(screen, color, self.launch_rect, border_radius=10)
        pygame.draw.rect(screen, (20, 24, 32), self.launch_rect, 2, border_radius=10)
        text = self.font.render(label, True, (255, 255, 255))
        screen.blit(text, text.get_rect(center=self.launch_rect.center))

        hint = self.font_small.render(
            "Click a part to buy | Backspace remove | L launch | Esc town",
            True,
            (150, 160, 180),
        )
        screen.blit(hint, (28, SCREEN_HEIGHT - 28))

        if self.notice_timer > 0:
            n = self.font.render(self.notice, True, (255, 236, 39))
            screen.blit(n, (SCREEN_WIDTH // 2 - n.get_width() // 2, 90))

        if self.countdown > 0:
            big = get_game_font(96, bold=True)
            num = big.render(str(int(self.countdown + 0.99)), True, (255, 120, 40))
            screen.blit(num, num.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))

        if self.story_ui.active:
            self.story_ui.draw(screen)

    def _draw_catalog(self, screen: pygame.Surface) -> None:
        panel = pygame.Rect(24, 100, 320, SCREEN_HEIGHT - 200)
        pygame.draw.rect(screen, (20, 24, 32), panel, border_radius=6)
        pygame.draw.rect(screen, (70, 82, 110), panel, 2, border_radius=6)
        head = self.font.render("Part Catalog", True, (200, 210, 230))
        screen.blit(head, (panel.x + 12, panel.y + 10))

        y = panel.y + 40 - self.scroll
        for i, key in enumerate(self.catalog_keys):
            part = PARTS_CATALOG[key]
            row = pygame.Rect(panel.x + 8, y, panel.width - 16, 30)
            if i == self.selected_catalog:
                pygame.draw.rect(screen, (48, 56, 76), row, border_radius=4)
            line = f"{part.name}  ${part.cost:,}"
            surf = self.font_small.render(line, True, (240, 244, 255))
            screen.blit(surf, (row.x + 8, row.y + 7))
            y += 34

    def _draw_assembled_rocket(self, screen: pygame.Surface) -> None:
        panel = pygame.Rect(370, 100, 360, SCREEN_HEIGHT - 200)
        pygame.draw.rect(screen, (20, 24, 32), panel, border_radius=6)
        pygame.draw.rect(screen, (70, 82, 110), panel, 2, border_radius=6)
        head = self.font.render("Assembled Rocket", True, (200, 210, 230))
        screen.blit(head, (panel.x + 12, panel.y + 10))

        cx = panel.centerx
        y = panel.bottom - 50
        for key in reversed(self.session.rocket_part_keys):
            part = PARTS_CATALOG[key]
            h = 28 if part.part_type != "engine" else 22
            color = {
                "command_pod": (220, 80, 80),
                "fuel_tank": (240, 150, 50),
                "engine": (140, 140, 150),
                "wing": (100, 120, 180),
                "leg": (120, 100, 80),
            }.get(part.part_type, (180, 180, 180))
            rect = pygame.Rect(cx - 22, y - h, 44, h)
            pygame.draw.rect(screen, color, rect, border_radius=3)
            pygame.draw.rect(screen, (30, 34, 44), rect, 1, border_radius=3)
            y -= h + 4

        if not self.session.rocket_part_keys:
            empty = self.font_small.render("(No parts yet)", True, (140, 150, 170))
            screen.blit(empty, empty.get_rect(center=panel.center))

    def _draw_stats(self, screen: pygame.Surface) -> None:
        mass = total_mass(self.session.rocket_part_keys)
        spent = total_cost(self.session.rocket_part_keys)
        lines = [
            f"Total mass: {mass:.0f} kg",
            f"Build value: ${spent:,}",
            f"Parts: {len(self.session.rocket_part_keys)}",
        ]
        y = 58
        for line in lines:
            surf = self.font_small.render(line, True, (200, 210, 230))
            screen.blit(surf, (SCREEN_WIDTH - 280, y))
            y += 22
