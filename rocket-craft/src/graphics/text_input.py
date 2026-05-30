"""Unicode text input widget for Pygame screens."""

from __future__ import annotations

import pygame


class TextInput:
    """A text input field that accepts printable Unicode characters."""

    def __init__(
        self,
        font: pygame.font.Font,
        x: int,
        y: int,
        width: int,
        max_length: int = 20,
        placeholder: str = "",
    ) -> None:
        self.font = font
        self.rect = pygame.Rect(x, y, width, 42)
        self.text = ""
        self.max_length = max_length
        self.placeholder = placeholder
        self.active = True
        self.cursor_visible = True
        self.cursor_timer = 0.0
        self.cursor_pos = 0

    def handle_event(self, event: pygame.event.Event) -> str:
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            return ""

        if not self.active or event.type != pygame.KEYDOWN:
            return ""

        if event.key == pygame.K_RETURN:
            self.active = False
            return self.text
        if event.key == pygame.K_BACKSPACE:
            if self.cursor_pos > 0:
                self.text = self.text[: self.cursor_pos - 1] + self.text[self.cursor_pos :]
                self.cursor_pos -= 1
        elif event.key == pygame.K_DELETE:
            if self.cursor_pos < len(self.text):
                self.text = self.text[: self.cursor_pos] + self.text[self.cursor_pos + 1 :]
        elif event.key == pygame.K_LEFT:
            self.cursor_pos = max(0, self.cursor_pos - 1)
        elif event.key == pygame.K_RIGHT:
            self.cursor_pos = min(len(self.text), self.cursor_pos + 1)
        elif event.key == pygame.K_HOME:
            self.cursor_pos = 0
        elif event.key == pygame.K_END:
            self.cursor_pos = len(self.text)
        elif event.unicode and event.unicode.isprintable() and len(self.text) < self.max_length:
            self.text = self.text[: self.cursor_pos] + event.unicode + self.text[self.cursor_pos :]
            self.cursor_pos += len(event.unicode)
        return ""

    def update(self, dt: float) -> None:
        self.cursor_timer += dt
        if self.cursor_timer > 0.5:
            self.cursor_timer = 0.0
            self.cursor_visible = not self.cursor_visible

    def render(self, screen: pygame.Surface) -> None:
        border_color = (255, 236, 39) if self.active else (118, 130, 158)
        pygame.draw.rect(screen, (28, 34, 48), self.rect, border_radius=5)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=5)

        display_text = self.text if self.text else self.placeholder
        color = (255, 255, 255) if self.text else (120, 132, 156)
        surf = self.font.render(display_text, True, color)
        if surf.get_width() > self.rect.width - 20:
            clipped = pygame.Surface((self.rect.width - 20, self.rect.height - 8), pygame.SRCALPHA)
            clipped.blit(surf, (self.rect.width - 20 - surf.get_width(), 0))
            surf = clipped
        screen.blit(surf, (self.rect.x + 10, self.rect.y + 8))

        if self.active and self.cursor_visible:
            before_cursor = self.font.render(self.text[: self.cursor_pos], True, (255, 255, 255))
            cursor_x = min(self.rect.right - 12, self.rect.x + 10 + before_cursor.get_width())
            cursor_y = self.rect.y + 8
            pygame.draw.line(
                screen,
                (255, 255, 255),
                (cursor_x, cursor_y),
                (cursor_x, cursor_y + self.font.get_height()),
                2,
            )

    def get_text(self) -> str:
        return self.text

    def set_text(self, text: str) -> None:
        self.text = text[: self.max_length]
        self.cursor_pos = len(self.text)

    def clear(self) -> None:
        self.text = ""
        self.cursor_pos = 0
