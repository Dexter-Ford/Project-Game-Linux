"""Scrollable bottom dialogue box."""

from __future__ import annotations

from typing import Any, List, Optional, Sequence, Tuple

import pygame

from config import SCREEN_HEIGHT, SCREEN_WIDTH
from systems.dialogue import wrap_text


Choice = Tuple[str, Any]


class DialogueBox:
    def __init__(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        self.screen = screen
        self.font = font
        self.visible = False
        self.npc_name = ""
        self.text_lines: List[str] = []
        self.choices: List[Choice] = []
        self.choice_rects: List[Tuple[pygame.Rect, Any]] = []
        self.scroll_offset = 0
        self.max_visible_lines = 5
        self.box_height = 286
        self.box_y = SCREEN_HEIGHT - self.box_height - 10
        self.text_area_height = self.box_height - 118

    def show(self, npc_name: str, text: str, choices: Sequence[Choice]) -> None:
        self.visible = True
        self.npc_name = npc_name
        self.choices = list(choices)
        self.choice_rects = []
        self.scroll_offset = 0
        self.text_lines = []
        max_width = SCREEN_WIDTH - 150
        for paragraph in str(text).split("\n"):
            self.text_lines.extend(wrap_text(paragraph, self.font, max_width) or [""])

    def hide(self) -> None:
        self.visible = False
        self.choice_rects = []

    def handle_event(self, event: pygame.event.Event) -> Optional[Any]:
        if not self.visible:
            return None

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:
                self.scroll_offset = max(0, self.scroll_offset - 1)
            elif event.button == 5:
                self.scroll_offset = min(self._max_scroll(), self.scroll_offset + 1)
            elif event.button == 1:
                payload = self._check_choice_click(event.pos)
                if payload is not None:
                    self.hide()
                    return payload

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.hide()
                return {"close": True}
            if pygame.K_1 <= event.key <= pygame.K_9:
                choice_idx = event.key - pygame.K_1
                if choice_idx < len(self.choices):
                    payload = self.choices[choice_idx][1]
                    self.hide()
                    return payload
        return None

    def render(self) -> None:
        if not self.visible:
            return

        box_rect = pygame.Rect(40, self.box_y, SCREEN_WIDTH - 80, self.box_height)
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        pygame.draw.rect(self.screen, (20, 20, 30), box_rect, border_radius=10)
        pygame.draw.rect(self.screen, (80, 80, 100), box_rect, 2, border_radius=10)

        name_surf = self.font.render(self.npc_name, True, (255, 200, 50))
        self.screen.blit(name_surf, (box_rect.x + 20, box_rect.y + 10))
        pygame.draw.line(
            self.screen,
            (100, 100, 100),
            (box_rect.x + 10, box_rect.y + 42),
            (box_rect.right - 10, box_rect.y + 42),
            1,
        )

        text_area = pygame.Rect(box_rect.x + 18, box_rect.y + 52, box_rect.width - 56, self.text_area_height)
        clip_before = self.screen.get_clip()
        self.screen.set_clip(text_area)
        line_height = self.font.get_height() + 5
        for i in range(self.max_visible_lines):
            line_idx = i + self.scroll_offset
            if line_idx < len(self.text_lines):
                y = text_area.y + i * line_height
                text_surf = self.font.render(self.text_lines[line_idx], True, (255, 255, 255))
                self.screen.blit(text_surf, (text_area.x, y))
        self.screen.set_clip(clip_before)

        self._draw_scrollbar(box_rect, text_area)
        self._draw_choices(box_rect)

    def _check_choice_click(self, pos: Tuple[int, int]) -> Optional[Any]:
        for rect, payload in self.choice_rects:
            if rect.collidepoint(pos):
                return payload
        return None

    def _max_scroll(self) -> int:
        return max(0, len(self.text_lines) - self.max_visible_lines)

    def _draw_scrollbar(self, box_rect: pygame.Rect, text_area: pygame.Rect) -> None:
        max_scroll = self._max_scroll()
        if max_scroll <= 0:
            return
        bar_rect = pygame.Rect(box_rect.right - 25, text_area.y, 10, text_area.height)
        thumb_height = max(30, int(bar_rect.height * self.max_visible_lines / max(1, len(self.text_lines))))
        thumb_y = int(bar_rect.y + (bar_rect.height - thumb_height) * (self.scroll_offset / max_scroll))
        pygame.draw.rect(self.screen, (60, 60, 60), bar_rect, border_radius=5)
        pygame.draw.rect(self.screen, (130, 130, 142), (bar_rect.x, thumb_y, bar_rect.width, thumb_height), border_radius=5)

    def _draw_choices(self, box_rect: pygame.Rect) -> None:
        self.choice_rects = []
        choice_y = box_rect.bottom - 76
        max_choices = min(3, len(self.choices))
        if max_choices == 0:
            return
        gap = 12
        width = (box_rect.width - 40 - gap * (max_choices - 1)) // max_choices
        for i, (choice_text, payload) in enumerate(self.choices[:max_choices]):
            rect = pygame.Rect(box_rect.x + 20 + i * (width + gap), choice_y, width, 52)
            hover = rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(self.screen, (48, 56, 76) if hover else (34, 38, 54), rect, border_radius=5)
            label = self.font.render(f"{i + 1}. {choice_text}", True, (255, 255, 150))
            if label.get_width() > rect.width - 14:
                label = pygame.transform.smoothscale(label, (rect.width - 14, label.get_height()))
            self.screen.blit(label, label.get_rect(center=rect.center))
            self.choice_rects.append((rect, payload))
