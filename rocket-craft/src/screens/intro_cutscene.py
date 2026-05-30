"""Procedural opening cutscene for the first new game."""

from __future__ import annotations

import math
import random
from typing import List, Tuple

import pygame

from config import SCREEN_HEIGHT, SCREEN_WIDTH
from graphics.ui import get_font
from systems.dialogue import wrap_text

try:
    from audio.audio_manager import AudioManager
except ImportError:
    AudioManager = None  # type: ignore[misc, assignment]


Scene = Tuple[str, float]


class IntroCutscene:
    def __init__(self, audio: "AudioManager | None" = None) -> None:
        self.audio = audio
        self.scenes: List[Scene] = [
            ("test", 22.0),
            ("fallout", 18.0),
            ("letter", 16.0),
            ("arrival", 38.0),
            ("transition", 7.0),
        ]
        self.scene_index = 0
        self.scene_time = 0.0
        self.finished = False
        self.font_logo = get_font(62, bold=True)
        self.font_big = get_font(34, bold=True)
        self.font = get_font(22)
        self.font_small = get_font(16)
        self.thai_font = get_font(22)
        self.title_font = get_font(36, bold=True)
        self._rng = random.Random(19)
        self._played_scene = ""
        if self.audio is not None:
            self.audio.play_music(self.audio.title_music_path(), fade_ms=800)

    def is_finished(self) -> bool:
        return self.finished

    def update(self, dt: float) -> None:
        if self.finished:
            return
        scene_name, duration = self.scenes[self.scene_index]
        if scene_name != self._played_scene:
            self._on_scene_enter(scene_name)
            self._played_scene = scene_name
        self.scene_time += dt
        if self.scene_time >= duration:
            self.scene_index += 1
            self.scene_time = 0.0
            if self.scene_index >= len(self.scenes):
                self.finished = True

    def handle_event(self, event: pygame.event.Event) -> str:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_SPACE):
            self.finished = True
            return "intro_done"
        return ""

    def draw(self, screen: pygame.Surface) -> None:
        if self.finished:
            screen.fill((0, 0, 0))
            return
        name, duration = self.scenes[self.scene_index]
        progress = min(1.0, self.scene_time / max(0.01, duration))
        if name == "test":
            self._draw_test(screen, progress)
        elif name == "fallout":
            self._draw_fallout(screen, progress)
        elif name == "letter":
            self._draw_letter(screen, progress)
        elif name == "arrival":
            self._draw_arrival(screen, progress)
        else:
            self._draw_transition(screen, progress)
        self._draw_skip_hint(screen)

    def _on_scene_enter(self, scene_name: str) -> None:
        if self.audio is None:
            return
        if scene_name == "test":
            self.audio.play_sfx("thrust", loop=True, volume=0.25)
        elif scene_name == "fallout":
            self.audio.stop_sfx("thrust")
            self.audio.play_sfx("error", volume=0.4)
        elif scene_name == "letter":
            self.audio.play_sfx("confirm", volume=0.25)
        elif scene_name == "arrival":
            self.audio.play_music(self.audio.zone_music_path("plaza") or self.audio.title_music_path(), fade_ms=1200)
        elif scene_name == "transition":
            self.audio.play_music(self.audio.title_music_path(), fade_ms=1000)

    def _draw_test(self, screen: pygame.Surface, t: float) -> None:
        screen.fill((14, 18, 30))
        pygame.draw.rect(screen, (28, 32, 46), (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
        logo = self.font_big.render("ORION HEAVY", True, (150, 158, 172))
        screen.blit(logo, logo.get_rect(center=(SCREEN_WIDTH // 2, 110)))
        self._silhouette(screen, 420, 430, (20, 30, 60), scale=1.35)
        self._silhouette(screen, 820, 430, (20, 30, 60), scale=1.1)

        stand_x, stand_y = SCREEN_WIDTH // 2, 430
        angle = -35 if t > 0.52 else 0
        rocket = pygame.Surface((70, 130), pygame.SRCALPHA)
        pygame.draw.rect(rocket, (218, 222, 230), (24, 34, 22, 70), border_radius=4)
        pygame.draw.polygon(rocket, (220, 70, 70), [(35, 4), (18, 36), (52, 36)])
        pygame.draw.rect(rocket, (150, 154, 164), (18, 102, 34, 14), border_radius=3)
        if 0.32 < t < 0.55:
            flame = int(22 + 18 * math.sin(self.scene_time * 18.0))
            pygame.draw.circle(rocket, (255, 136, 35), (35, 126), flame)
        rotated = pygame.transform.rotate(rocket, angle)
        screen.blit(rotated, rotated.get_rect(center=(stand_x, stand_y)))
        pygame.draw.line(screen, (80, 86, 100), (stand_x - 70, 500), (stand_x + 70, 500), 6)

        if t > 0.2:
            self._caption(screen, "Orion Heavy, 03:47 AM")
        if t > 0.66:
            viewers = "LIVE VIEWERS: 12 -> 2,847 -> 147,000"
            text = self.font_big.render(viewers, True, (255, 236, 39))
            screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 570)))
        if t > 0.78:
            self._social_post(screen)
        if 0.52 < t < 0.56:
            flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash.fill((255, 255, 255, 210))
            screen.blit(flash, (0, 0))
        self._fade_edges(screen, t)

    def _draw_fallout(self, screen: pygame.Surface, t: float) -> None:
        screen.fill((44, 46, 52))
        third = int(t * 3)
        if third == 0:
            self._office(screen, "HR OFFICE", "Security will escort you out.", desk=True)
        elif third == 1:
            self._office(screen, "HALLWAY", "Dr. Chen submitted his resignation the same day.", hallway=True)
        else:
            self._office(screen, "MISSION CONTROL", "Maria was reassigned to Document Archival.", console=True)
        self._fade_edges(screen, t)

    def _draw_letter(self, screen: pygame.Surface, t: float) -> None:
        screen.fill((20, 22, 32))
        pygame.draw.rect(screen, (42, 45, 58), (150, 140, 220, 260), border_radius=4)
        pygame.draw.rect(screen, (168, 184, 220), (170, 160, 180, 100), border_radius=3)
        moon = pygame.Surface((80, 80), pygame.SRCALPHA)
        pygame.draw.circle(moon, (230, 230, 210), (40, 40), 32)
        screen.blit(moon, (210, 170))

        if t < 0.72:
            paper = pygame.Rect(SCREEN_WIDTH // 2 - 210, 120, 420, 420)
            points = [
                (paper.x + self._rng.randint(-3, 3), paper.y + self._rng.randint(-3, 3)),
                (paper.right + self._rng.randint(-3, 3), paper.y + self._rng.randint(-3, 3)),
                (paper.right + self._rng.randint(-3, 3), paper.bottom + self._rng.randint(-3, 3)),
                (paper.x + self._rng.randint(-3, 3), paper.bottom + self._rng.randint(-3, 3)),
            ]
            pygame.draw.polygon(screen, (255, 250, 230), points)
            pygame.draw.polygon(screen, (190, 170, 130), points, 2)
            lines = [
                "old launch base at plaza...",
                "one hangar left...",
                "50,000 from the town council...",
                "just the four of us...",
                "come be director.",
            ]
            visible = min(len(lines), int(t * 8))
            for i, line in enumerate(lines[:visible]):
                surf = self.font.render(line, True, (72, 64, 52))
                screen.blit(surf, (paper.x + 42, paper.y + 70 + i * 48))
        else:
            offset = int((t - 0.72) * 900)
            for x in range(-200, SCREEN_WIDTH + 200, 180):
                self._tree(screen, x - offset % 180, 420)
            pygame.draw.rect(screen, (74, 110, 58), (0, 470, SCREEN_WIDTH, 250))
            pygame.draw.rect(screen, (90, 64, 50), (0, 520, SCREEN_WIDTH, 50))
            self._caption(screen, "Bus window, somewhere far from Orion")
        self._fade_edges(screen, t)

    def _draw_arrival(self, screen: pygame.Surface, t: float) -> None:
        sky_top = (126, 142, 158) if t < 0.82 else (116, 176, 220)
        sky_bottom = (172, 184, 188) if t < 0.82 else (200, 228, 246)
        for y in range(SCREEN_HEIGHT):
            mix = y / SCREEN_HEIGHT
            color = tuple(int(sky_top[i] * (1 - mix) + sky_bottom[i] * mix) for i in range(3))
            pygame.draw.line(screen, color, (0, y), (SCREEN_WIDTH, y))
        pygame.draw.rect(screen, (74, 130, 72), (0, 430, SCREEN_WIDTH, 290))
        pygame.draw.rect(screen, (92, 96, 104), (760, 330, 230, 120), border_radius=6)
        pygame.draw.polygon(screen, (62, 66, 76), [(740, 330), (875, 255), (1015, 330)])

        bus_x = int(-260 + min(t, 0.22) / 0.22 * 420)
        self._bus(screen, bus_x, 405)
        self._silhouette(screen, 320, 456, (40, 48, 70), scale=0.95)

        if t > 0.16:
            self._silhouette(screen, 430, 456, (180, 170, 140), scale=1.0)
        if t > 0.38:
            self._silhouette(screen, 570, 456, (255, 110, 150), scale=1.0)
        if t > 0.58:
            self._silhouette(screen, 700, 456, (110, 210, 255), scale=1.0)
        if t > 0.76:
            self._silhouette(screen, 840, 456, (255, 170, 70), scale=1.0)
        if 0.16 < t < 0.38:
            self.draw_dialogue_line(screen, 'ลุงเจนกินส์: "ยินดีต้อนรับสู่ศูนย์อวกาศที่ไม่มีกาแฟดี ๆ"', 500)
        elif 0.38 <= t < 0.58:
            self.draw_dialogue_line(screen, 'มาเรีย: "งบ 50,000 หมดในสามเดือน ถ้าไม่ยิงอะไรขึ้นฟ้า"', 500)
        elif 0.58 <= t < 0.76:
            self.draw_dialogue_line(screen, 'ดร.เฉิน: "ดีใจที่นายมา เรามีเชื้อเพลิงเหลือครึ่งถัง!"', 500)
        elif 0.76 <= t < 0.86:
            self.draw_dialogue_line(screen, 'บ็อบ: "เครื่องยนต์รออยู่ คราวนี้ไม่มีบอร์ดมาสั่งพับ"', 500)
        if t > 0.86:
            sun = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.circle(sun, (255, 230, 125, 130), (1050, 130), int(80 + (t - 0.86) * 280))
            screen.blit(sun, (0, 0))
            title = self.font_logo.render("ROCKETCRAFT", True, (255, 255, 255))
            screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 190)))
            sub = self.font_big.render("Build. Launch. Prove them wrong.", True, (255, 236, 39))
            screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, 260)))

        if t < 0.82:
            for i in range(120):
                x = (i * 37 + int(self.scene_time * 90)) % SCREEN_WIDTH
                y = (i * 23 + int(self.scene_time * 180)) % SCREEN_HEIGHT
                pygame.draw.line(screen, (190, 210, 230), (x, y), (x - 5, y + 14), 1)
        self._fade_edges(screen, t)

    def _draw_transition(self, screen: pygame.Surface, t: float) -> None:
        screen.fill((0, 0, 0))
        alpha = int(255 * min(1.0, t * 2.0))
        title = self.font_big.render("CREATE DIRECTOR", True, (255, 236, 39))
        title.set_alpha(alpha)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))

    def _caption(self, screen: pygame.Surface, text: str) -> None:
        surf = self.font.render(text, True, (235, 238, 246))
        rect = surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 76))
        pygame.draw.rect(screen, (0, 0, 0), rect.inflate(28, 18), border_radius=4)
        screen.blit(surf, rect)

    def _thai_caption(self, screen: pygame.Surface, text: str) -> None:
        self.draw_dialogue_line(screen, text, SCREEN_HEIGHT - 116)

    def draw_dialogue_line(self, screen: pygame.Surface, text: str, y_position: int, alpha: int = 255) -> int:
        """Draw one Thai dialogue beat with safe wrapping and spacing."""
        lines = wrap_text(text, self.thai_font, SCREEN_WIDTH - 160)
        rendered = [self.thai_font.render(line, True, (255, 255, 255)) for line in lines[:2]]
        if not rendered:
            return y_position
        height = sum(surf.get_height() for surf in rendered) + 14 * (len(rendered) - 1)
        width = max(surf.get_width() for surf in rendered)
        bg_rect = pygame.Rect(0, 0, width + 48, height + 22)
        bg_rect.center = (SCREEN_WIDTH // 2, y_position + bg_rect.height // 2)
        bg = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (0, 0, 0, min(220, alpha)), bg.get_rect(), border_radius=6)
        screen.blit(bg, bg_rect)
        y = bg_rect.y + 11
        for surf in rendered:
            surf.set_alpha(alpha)
            screen.blit(surf, surf.get_rect(centerx=bg_rect.centerx, y=y))
            y += surf.get_height() + 14
        return bg_rect.bottom + 25

    def _draw_skip_hint(self, screen: pygame.Surface) -> None:
        hint = self.font_small.render("SPACE or ESC skip", True, (170, 178, 194))
        screen.blit(hint, (SCREEN_WIDTH - hint.get_width() - 22, SCREEN_HEIGHT - 28))

    def _fade_edges(self, screen: pygame.Surface, t: float) -> None:
        alpha = 0
        if t < 0.08:
            alpha = int(255 * (1.0 - t / 0.08))
        elif t > 0.92:
            alpha = int(255 * ((t - 0.92) / 0.08))
        if alpha:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, alpha))
            screen.blit(overlay, (0, 0))

    def _silhouette(self, screen: pygame.Surface, x: int, y: int, color: Tuple[int, int, int], scale: float = 1.0) -> None:
        head = int(18 * scale)
        body_w = int(34 * scale)
        body_h = int(62 * scale)
        pygame.draw.circle(screen, color, (x, y - body_h - head), head)
        pygame.draw.rect(screen, color, (x - body_w // 2, y - body_h, body_w, body_h), border_radius=8)
        pygame.draw.polygon(screen, color, [(x - body_w // 2, y - 6), (x - body_w, y + 34), (x - 4, y + 34)])
        pygame.draw.polygon(screen, color, [(x + body_w // 2, y - 6), (x + body_w, y + 34), (x + 4, y + 34)])

    def _social_post(self, screen: pygame.Surface) -> None:
        rect = pygame.Rect(SCREEN_WIDTH // 2 - 260, 610, 520, 70)
        pygame.draw.rect(screen, (245, 246, 250), rect, border_radius=8)
        pygame.draw.rect(screen, (160, 166, 180), rect, 2, border_radius=8)
        lines = [
            "at least it did not explode",
            "bro really said 'trust the science' then fell over",
        ]
        for i, line in enumerate(lines):
            surf = self.font_small.render(line, True, (42, 46, 58))
            screen.blit(surf, (rect.x + 20, rect.y + 12 + i * 24))

    def _office(self, screen: pygame.Surface, title: str, line: str, desk: bool = False, hallway: bool = False, console: bool = False) -> None:
        label = self.font_big.render(title, True, (205, 210, 220))
        screen.blit(label, (80, 70))
        if desk:
            pygame.draw.rect(screen, (60, 62, 70), (520, 430, 310, 80), border_radius=4)
            self._silhouette(screen, 430, 500, (20, 30, 60), 1.0)
            self._silhouette(screen, 700, 420, (20, 30, 60), 1.25)
        elif hallway:
            pygame.draw.rect(screen, (76, 78, 86), (0, 360, SCREEN_WIDTH, 140))
            self._silhouette(screen, 470, 455, (20, 30, 60), 1.0)
            self._silhouette(screen, 720, 455, (110, 210, 255), 0.9)
        elif console:
            pygame.draw.rect(screen, (28, 34, 48), (520, 390, 360, 95), border_radius=5)
            for x in range(545, 850, 55):
                pygame.draw.rect(screen, (80, 180, 210), (x, 410, 34, 18), border_radius=3)
            self._silhouette(screen, 640, 430, (255, 110, 150), 1.05)
        self._caption(screen, line)

    def _tree(self, screen: pygame.Surface, x: int, y: int) -> None:
        pygame.draw.rect(screen, (90, 58, 34), (x - 5, y - 44, 10, 44))
        pygame.draw.circle(screen, (54, 112, 60), (x, y - 62), 28)

    def _bus(self, screen: pygame.Surface, x: int, y: int) -> None:
        pygame.draw.rect(screen, (238, 190, 72), (x, y - 72, 230, 72), border_radius=8)
        pygame.draw.rect(screen, (55, 80, 105), (x + 24, y - 60, 48, 26), border_radius=3)
        pygame.draw.rect(screen, (55, 80, 105), (x + 88, y - 60, 48, 26), border_radius=3)
        pygame.draw.rect(screen, (55, 80, 105), (x + 152, y - 60, 48, 26), border_radius=3)
        pygame.draw.circle(screen, (28, 28, 32), (x + 52, y), 18)
        pygame.draw.circle(screen, (28, 28, 32), (x + 178, y), 18)
