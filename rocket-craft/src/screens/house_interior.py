"""Player house interior — walk around, sleep at bed to save, exit to town."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import pygame

from config import SCREEN_HEIGHT, SCREEN_WIDTH
from core.fonts import get_dialogue_font, get_game_font
from core.game_session import GameSession
from core.save_load import SaveManager
from graphics.room_depth import (
    draw_bed_3d,
    draw_bookshelf_3d,
    draw_box_3d,
    draw_door_3d,
    draw_recessed_window,
    draw_room_shell,
    draw_table_lamp_3d,
    lerp_color,
)

try:
    from audio.audio_manager import AudioManager
except ImportError:
    AudioManager = None  # type: ignore[misc, assignment]

Color = Tuple[int, int, int]

ROOM_W = 800
ROOM_H = 600
INTERACT_RADIUS = 50.0

DECOR_STYLES = ("cozy", "science", "workshop", "botanical")
STYLE_LABELS: Dict[str, str] = {
    "cozy": "Cozy Launch Loft",
    "science": "Quiet Science Nook",
    "workshop": "Engineer Workshop",
    "botanical": "Moon Garden Room",
}


class HouseInteriorScreen:
    def __init__(
        self,
        session: GameSession,
        save_manager: SaveManager,
        audio: "AudioManager | None" = None,
    ) -> None:
        self.session = session
        self.save_manager = save_manager
        self.audio = audio
        self.font = get_game_font(16)
        self.font_small = get_game_font(14)
        self.font_title = get_game_font(22, bold=True)
        self.font_dialogue = get_dialogue_font(18)
        self.font_dialogue_choice = get_dialogue_font(17)

        self.room_x = (SCREEN_WIDTH - ROOM_W) // 2
        self.room_y = (SCREEN_HEIGHT - ROOM_H) // 2

        self.player_x = 400.0
        self.player_y = 480.0
        self.player_target_x = self.player_x
        self.player_target_y = self.player_y
        self.move_speed = 140.0

        self.bed_x = 640.0
        self.bed_y = 320.0
        self.decor_x = 220.0
        self.decor_y = 360.0
        self.door_rect = pygame.Rect(360, 540, 80, 56)

        self.owner_name = session.player_name
        self.owner_key = "player"
        self.can_sleep_save = True
        self.sleep_dialogue = False
        self.decor_dialogue = False
        self.sleep_choice = 0
        self.decor_choice = 0
        self.status_message = ""
        self.status_timer = 0.0
        self.sleep_fade = 0.0

    def on_enter(self, owner_name: Optional[str] = None, owner_key: str = "player") -> None:
        self.owner_key = owner_key
        self.owner_name = owner_name or self.session.player_name
        self.can_sleep_save = owner_key == "player"
        self.player_x = 400.0
        self.player_y = 480.0
        self.player_target_x = self.player_x
        self.player_target_y = self.player_y
        self.sleep_dialogue = False
        self.decor_dialogue = False
        self.decor_choice = max(0, DECOR_STYLES.index(self._decor_style()) if self._decor_style() in DECOR_STYLES else 0)
        self.status_message = ""
        self.status_timer = 0.0
        self.sleep_fade = 0.0

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if self.sleep_fade > 0:
            return None

        if self.sleep_dialogue:
            return self._handle_sleep_dialogue(event)
        if self.decor_dialogue:
            return self._handle_decor_dialogue(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "town"
            if event.key == pygame.K_e:
                if self.can_sleep_save and self._near_bed():
                    self._open_sleep_dialogue()
                elif self.can_sleep_save and self._near_decor_desk():
                    self._open_decor_dialogue()
                elif self._near_door():
                    return "town"
                return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            local = self._screen_to_room(event.pos)
            if self.room_rect().collidepoint(*local):
                self.player_target_x, self.player_target_y = local
        return None

    def _handle_decor_dialogue(self, event: pygame.event.Event) -> Optional[str]:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.decor_choice = max(0, self.decor_choice - 1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.decor_choice = min(len(DECOR_STYLES), self.decor_choice + 1)
            elif pygame.K_1 <= event.key <= pygame.K_5:
                self.decor_choice = event.key - pygame.K_1
                return self._activate_decor_choice()
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self._activate_decor_choice()
            elif event.key == pygame.K_ESCAPE:
                self.decor_dialogue = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            panel = self._dialogue_panel_rect()
            choice_y = panel.y + 64
            for i in range(len(DECOR_STYLES) + 1):
                rect = pygame.Rect(panel.x + 16, choice_y + i * 28, panel.width - 32, 24)
                if rect.collidepoint(event.pos):
                    self.decor_choice = i
                    return self._activate_decor_choice()
        return None

    def _activate_decor_choice(self) -> Optional[str]:
        if self.decor_choice >= len(DECOR_STYLES):
            self.decor_dialogue = False
            return None
        self.session.home_decor_style = DECOR_STYLES[self.decor_choice]
        self.decor_dialogue = False
        self.status_message = f"Decor changed to {STYLE_LABELS[self.session.home_decor_style]}."
        self.status_timer = 2.8
        if self.audio:
            self.audio.play_sfx("confirm")
        return None

    def _handle_sleep_dialogue(self, event: pygame.event.Event) -> Optional[str]:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.sleep_choice = 0
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.sleep_choice = 1
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self._activate_sleep_choice()
            elif event.key == pygame.K_ESCAPE:
                self.sleep_dialogue = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            panel = self._dialogue_panel_rect()
            choice_y = panel.bottom - 76
            for i in range(2):
                rect = pygame.Rect(panel.x + 16, choice_y + i * 34, panel.width - 32, 28)
                if rect.collidepoint(event.pos):
                    self.sleep_choice = i
                    return self._activate_sleep_choice()
        return None

    def _activate_sleep_choice(self) -> Optional[str]:
        if self.sleep_choice == 1:
            self.sleep_dialogue = False
            if self.audio:
                self.audio.play_sfx("click")
            return None
        self.sleep_dialogue = False
        self._perform_bed_save()
        return None

    def _perform_bed_save(self) -> None:
        if self.can_sleep_save:
            self.session.time.sleep_until_morning()
        self.save_manager.bed_save(self.session.to_save_dict())
        if self.audio:
            self.audio.play_sfx("click")
            self.audio.play_sfx("confirm")
        name = self.session.player_name
        self.status_message = f"Game saved. Rest well, {name}."
        self.status_timer = 4.0
        self.sleep_fade = 0.5

    def update(self, dt: float) -> None:
        if self.sleep_fade > 0:
            self.sleep_fade = max(0.0, self.sleep_fade - dt)
            return

        if self.status_timer > 0:
            self.status_timer -= dt

        dx = self.player_target_x - self.player_x
        dy = self.player_target_y - self.player_y
        dist = math.hypot(dx, dy)
        if dist > 2.0:
            step = min(self.move_speed * dt, dist)
            self.player_x += dx / dist * step
            self.player_y += dy / dist * step
        self.player_x = max(40.0, min(ROOM_W - 40.0, self.player_x))
        self.player_y = max(40.0, min(ROOM_H - 40.0, self.player_y))

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((24, 28, 38))
        room = self.room_rect()
        floor_rect, left_wall, _right_wall = self._draw_room(screen, room)
        self._draw_furniture(screen, room, floor_rect, left_wall)
        self._draw_decorations(screen, room, floor_rect)
        self._draw_bed(screen, room)
        draw_door_3d(screen, room, self.door_rect)
        self._draw_player(screen, room)
        self._draw_prompts(screen, room)
        self._draw_hud(screen)

        if self.sleep_dialogue:
            self._draw_sleep_dialogue(screen)
        elif self.decor_dialogue:
            self._draw_decor_dialogue(screen)
        elif self.status_timer > 0 and self.status_message:
            self._draw_status(screen)

        if self.sleep_fade > 0:
            half = 0.25
            elapsed = 0.5 - self.sleep_fade
            if elapsed < half:
                alpha = int(255 * (elapsed / half))
            else:
                alpha = int(255 * (1.0 - (elapsed - half) / half))
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, max(0, min(255, alpha))))
            screen.blit(overlay, (0, 0))

    def room_rect(self) -> pygame.Rect:
        return pygame.Rect(self.room_x, self.room_y, ROOM_W, ROOM_H)

    def _screen_to_room(self, pos: Tuple[int, int]) -> Tuple[float, float]:
        return float(pos[0] - self.room_x), float(pos[1] - self.room_y)

    def _room_to_screen(self, rx: float, ry: float) -> Tuple[int, int]:
        return int(self.room_x + rx), int(self.room_y + ry)

    def _near_bed(self) -> bool:
        dx = self.player_x - self.bed_x
        dy = self.player_y - (self.bed_y + 20)
        return dx * dx + dy * dy <= INTERACT_RADIUS * INTERACT_RADIUS

    def _near_decor_desk(self) -> bool:
        dx = self.player_x - self.decor_x
        dy = self.player_y - self.decor_y
        return dx * dx + dy * dy <= INTERACT_RADIUS * INTERACT_RADIUS

    def _near_door(self) -> bool:
        cx = self.door_rect.centerx
        cy = self.door_rect.centery
        dx = self.player_x - cx
        dy = self.player_y - cy
        return dx * dx + dy * dy <= INTERACT_RADIUS * INTERACT_RADIUS

    def _open_sleep_dialogue(self) -> None:
        self.sleep_dialogue = True
        self.sleep_choice = 0
        if self.audio:
            self.audio.play_sfx("click")

    def _open_decor_dialogue(self) -> None:
        style = self._decor_style()
        self.decor_choice = DECOR_STYLES.index(style) if style in DECOR_STYLES else 0
        self.decor_dialogue = True
        if self.audio:
            self.audio.play_sfx("click")

    def _decor_style(self) -> str:
        if self.owner_key == "player":
            return self.session.home_decor_style if self.session.home_decor_style in DECOR_STYLES else "cozy"
        return {
            "dr_chen": "science",
            "bob": "workshop",
            "maria": "cozy",
            "jenkins": "botanical",
        }.get(self.owner_key, "cozy")

    def _dialogue_panel_rect(self) -> pygame.Rect:
        return pygame.Rect(50, SCREEN_HEIGHT - 250, SCREEN_WIDTH - 100, 200)

    def _draw_room(self, screen: pygame.Surface, room: pygame.Rect) -> Tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        floor_rect, left_wall, right_wall = draw_room_shell(screen, room)
        draw_recessed_window(screen, left_wall, (12, 28), (52, 68), is_night=False)
        return floor_rect, left_wall, right_wall

    def _draw_furniture(
        self,
        screen: pygame.Surface,
        room: pygame.Rect,
        floor_rect: pygame.Rect,
        left_wall: pygame.Rect,
    ) -> None:
        table = pygame.Rect(*self._room_to_screen(200, 300), 76, 50)
        draw_box_3d(
            screen,
            table,
            lerp_color((150, 108, 72), (180, 130, 90), 0.4),
            (120, 85, 55),
            (88, 60, 38),
            depth=12,
        )
        draw_table_lamp_3d(screen, table.right - 8, table.y - 8)

        shelf = pygame.Rect(*self._room_to_screen(108, 148), 96, 148)
        draw_bookshelf_3d(screen, shelf)

    def _draw_decorations(self, screen: pygame.Surface, room: pygame.Rect, floor_rect: pygame.Rect) -> None:
        style = self._decor_style()
        # Rug and floor composition anchor the room visually.
        rug_color = {
            "cozy": (196, 86, 76),
            "science": (64, 126, 160),
            "workshop": (116, 94, 72),
            "botanical": (70, 150, 92),
        }.get(style, (196, 86, 76))
        rug = pygame.Rect(*self._room_to_screen(300, 400), 240, 100)
        pygame.draw.ellipse(screen, tuple(max(0, c - 40) for c in rug_color), rug.inflate(18, 14))
        pygame.draw.ellipse(screen, rug_color, rug)
        pygame.draw.ellipse(screen, lerp_color(rug_color, (255, 255, 255), 0.15), rug.inflate(-30, -22), 3)
        pygame.draw.ellipse(screen, (245, 235, 205), rug.inflate(-38, -28), 2)

        if self.can_sleep_save:
            board_x, board_y = self._room_to_screen(self.decor_x - 46, self.decor_y - 34)
            board = pygame.Rect(board_x, board_y, 92, 66)
            draw_box_3d(
                screen,
                board,
                lerp_color((70, 80, 110), (90, 100, 130), 0.4),
                (36, 42, 58),
                (24, 28, 40),
                depth=10,
            )
            pygame.draw.rect(screen, (135, 150, 182), board.inflate(-6, -6), 2, border_radius=4)
            for i, color in enumerate(((255, 236, 39), (110, 210, 255), (255, 170, 70), (120, 220, 120))):
                pygame.draw.rect(screen, color, (board.x + 12 + i * 18, board.y + 16, 12, 30), border_radius=2)
            label = self.font_small.render("Decor", True, (230, 236, 248))
            screen.blit(label, label.get_rect(center=(board.centerx, board.bottom - 9)))

        if style == "science":
            self._draw_science_decor(screen)
        elif style == "workshop":
            self._draw_workshop_decor(screen)
        elif style == "botanical":
            self._draw_botanical_decor(screen)
        else:
            self._draw_cozy_decor(screen)

    def _draw_cozy_decor(self, screen: pygame.Surface) -> None:
        for x, y, w, h, color in (
            (300, 150, 90, 58, (230, 214, 176)),
            (420, 120, 120, 70, (202, 218, 238)),
        ):
            frame = pygame.Rect(*self._room_to_screen(x, y), w, h)
            draw_box_3d(screen, frame, (120, 100, 80), (90, 62, 42), (70, 50, 35), depth=8)
            pygame.draw.rect(screen, color, frame.inflate(-10, -10), border_radius=2)
        couch = pygame.Rect(*self._room_to_screen(305, 270), 136, 62)
        draw_box_3d(screen, couch, (120, 140, 180), (94, 118, 160), (64, 80, 118), depth=14)
        pygame.draw.circle(screen, (255, 236, 39), self._room_to_screen(524, 162), 18)

    def _draw_science_decor(self, screen: pygame.Surface) -> None:
        # Telescope, lab jars, and star chart for Dr. Chen / science style.
        base = self._room_to_screen(520, 250)
        pygame.draw.line(screen, (210, 216, 225), base, (base[0] + 70, base[1] - 42), 5)
        pygame.draw.circle(screen, (84, 112, 140), (base[0] + 72, base[1] - 44), 12)
        pygame.draw.line(screen, (120, 128, 140), base, (base[0] - 20, base[1] + 55), 3)
        pygame.draw.line(screen, (120, 128, 140), base, (base[0] + 24, base[1] + 55), 3)
        chart = pygame.Rect(*self._room_to_screen(325, 116), 150, 84)
        pygame.draw.rect(screen, (18, 26, 46), chart, border_radius=4)
        pygame.draw.rect(screen, (110, 140, 180), chart, 2, border_radius=4)
        for sx, sy in ((350, 140), (384, 162), (430, 132), (452, 178)):
            pygame.draw.circle(screen, (245, 248, 255), self._room_to_screen(sx, sy), 2)
        for i, color in enumerate(((90, 210, 180), (150, 190, 255), (240, 210, 90))):
            x, y = self._room_to_screen(150 + i * 26, 272)
            pygame.draw.rect(screen, color, (x, y, 14, 24), border_radius=3)
            pygame.draw.rect(screen, (235, 245, 255), (x, y, 14, 24), 1, border_radius=3)

    def _draw_workshop_decor(self, screen: pygame.Surface) -> None:
        bench = pygame.Rect(*self._room_to_screen(430, 236), 150, 54)
        draw_box_3d(screen, bench, (130, 95, 62), (96, 66, 42), (62, 44, 30), depth=12)
        for i in range(5):
            x = bench.x + 12 + i * 26
            pygame.draw.line(screen, (180, 190, 196), (x, bench.y + 8), (x + 18, bench.y + 28), 3)
        engine = pygame.Rect(*self._room_to_screen(520, 330), 54, 68)
        pygame.draw.rect(screen, (94, 98, 108), engine, border_radius=6)
        pygame.draw.rect(screen, (50, 54, 62), engine, 2, border_radius=6)
        pygame.draw.circle(screen, (255, 150, 60), engine.midbottom, 14)
        drawing = pygame.Rect(*self._room_to_screen(305, 125), 100, 70)
        pygame.draw.rect(screen, (245, 245, 232), drawing, border_radius=3)
        pygame.draw.rect(screen, (110, 92, 72), drawing, 2, border_radius=3)
        pygame.draw.polygon(screen, (220, 70, 70), [(drawing.centerx, drawing.y + 12), (drawing.x + 36, drawing.y + 48), (drawing.x + 64, drawing.y + 48)])

    def _draw_botanical_decor(self, screen: pygame.Surface) -> None:
        for x, y, size in ((330, 265, 42), (520, 205, 34), (580, 390, 46), (255, 410, 30)):
            px, py = self._room_to_screen(x, y)
            pygame.draw.rect(screen, (130, 82, 48), (px - 11, py + size // 2, 22, 20), border_radius=4)
            pygame.draw.circle(screen, (60, 150, 80), (px, py), size // 2)
            pygame.draw.circle(screen, (82, 180, 102), (px - size // 5, py - size // 8), size // 4)
        moon_map = pygame.Rect(*self._room_to_screen(385, 116), 120, 74)
        pygame.draw.rect(screen, (230, 224, 196), moon_map, border_radius=4)
        pygame.draw.rect(screen, (120, 104, 78), moon_map, 2, border_radius=4)
        pygame.draw.circle(screen, (154, 144, 120), moon_map.center, 24, 2)
        pygame.draw.circle(screen, (154, 144, 120), (moon_map.x + 78, moon_map.y + 32), 7, 1)

    def _blanket_color(self) -> Color:
        if self.session.player_color:
            return self.session.player_color
        return (60, 120, 220)

    def _draw_bed(self, screen: pygame.Surface, room: pygame.Rect) -> None:
        bed = pygame.Rect(*self._room_to_screen(self.bed_x - 32, self.bed_y), 68, 88)
        draw_bed_3d(screen, bed, self._blanket_color())

    def _draw_player(self, screen: pygame.Surface, room: pygame.Rect) -> None:
        x, y = self._room_to_screen(self.player_x, self.player_y)
        pygame.draw.circle(screen, (20, 24, 32), (x, y), 13)
        pygame.draw.polygon(screen, self.session.player_color, [(x, y - 14), (x - 11, y + 10), (x + 11, y + 10)])

    def _draw_prompts(self, screen: pygame.Surface, room: pygame.Rect) -> None:
        if self.sleep_dialogue or self.decor_dialogue or self.sleep_fade > 0:
            return
        if self.can_sleep_save and self._near_decor_desk():
            self._draw_floating_text(screen, self.decor_x, self.decor_y - 52, "Press E to Decorate")
        if self.can_sleep_save and self._near_bed():
            self._draw_floating_text(screen, self.bed_x, self.bed_y - 50, "Press E to Sleep & Save")
        if self._near_door():
            self._draw_floating_text(screen, float(self.door_rect.centerx), float(self.door_rect.top - 20), "Press E to Leave")

    def _draw_floating_text(self, screen: pygame.Surface, rx: float, ry: float, text: str) -> None:
        surf = self.font_small.render(text, True, (255, 255, 220))
        x, y = self._room_to_screen(rx, ry)
        rect = surf.get_rect(center=(x, y))
        pygame.draw.rect(screen, (20, 24, 36), rect.inflate(12, 8), border_radius=4)
        screen.blit(surf, rect)

    def _draw_hud(self, screen: pygame.Surface) -> None:
        title = self.font_title.render(f"{self.owner_name}'s Home", True, (255, 236, 39))
        screen.blit(title, (28, 22))
        style = STYLE_LABELS.get(self._decor_style(), "Home")
        hint_text = f"{style} | ESC return to town"
        hint = self.font_small.render(hint_text, True, (180, 190, 210))
        screen.blit(hint, (28, 52))

    def _draw_sleep_dialogue(self, screen: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
        panel = self._dialogue_panel_rect()
        pygame.draw.rect(screen, (30, 34, 44), panel, border_radius=8)
        pygame.draw.rect(screen, (120, 132, 160), panel, 2, border_radius=8)
        speaker = self.font_dialogue.render("Bed", True, (255, 200, 50))
        screen.blit(speaker, (panel.x + 20, panel.y + 14))
        body = self.font_dialogue.render("Sleep and save your progress?", True, (255, 255, 255))
        screen.blit(body, (panel.x + 20, panel.y + 52))
        choices = ["Sleep & Save", "Cancel"]
        choice_y = panel.bottom - 76
        for i, label in enumerate(choices):
            rect = pygame.Rect(panel.x + 16, choice_y + i * 34, panel.width - 32, 28)
            pygame.draw.rect(
                screen,
                (48, 56, 76) if i == self.sleep_choice else (36, 42, 58),
                rect,
                border_radius=4,
            )
            color = (255, 255, 100) if i == self.sleep_choice else (220, 220, 230)
            text = self.font_dialogue_choice.render(f"{i + 1}. {label}", True, color)
            screen.blit(text, (rect.x + 10, rect.y + 5))

    def _draw_decor_dialogue(self, screen: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
        panel = self._dialogue_panel_rect()
        pygame.draw.rect(screen, (30, 34, 44), panel, border_radius=8)
        pygame.draw.rect(screen, (120, 132, 160), panel, 2, border_radius=8)
        speaker = self.font_dialogue.render("Decor Desk", True, (255, 200, 50))
        screen.blit(speaker, (panel.x + 20, panel.y + 14))
        body = self.font_dialogue.render("Choose a room arrangement.", True, (255, 255, 255))
        screen.blit(body, (panel.x + 20, panel.y + 42))

        labels = [STYLE_LABELS[key] for key in DECOR_STYLES] + ["Cancel"]
        choice_y = panel.y + 70
        for i, label in enumerate(labels):
            rect = pygame.Rect(panel.x + 16, choice_y + i * 26, panel.width - 32, 24)
            pygame.draw.rect(
                screen,
                (48, 56, 76) if i == self.decor_choice else (36, 42, 58),
                rect,
                border_radius=4,
            )
            color = (255, 255, 100) if i == self.decor_choice else (220, 220, 230)
            text = self.font_dialogue_choice.render(f"{i + 1}. {label}", True, color)
            screen.blit(text, (rect.x + 10, rect.y + 3))

    def _draw_status(self, screen: pygame.Surface) -> None:
        confirm = "Progress saved successfully."
        lines = [confirm, self.status_message] if self.status_message else [confirm]
        y = SCREEN_HEIGHT // 2 - 30
        for line in lines:
            surf = self.font.render(line, True, (255, 236, 39))
            rect = surf.get_rect(center=(SCREEN_WIDTH // 2, y))
            pygame.draw.rect(screen, (18, 22, 30), rect.inflate(28, 14), border_radius=6)
            screen.blit(surf, rect)
            y += 36
