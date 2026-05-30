"""HUD overlays."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pygame

from config import CYAN, SCREEN_HEIGHT, SCREEN_WIDTH, WHITE, YELLOW
from core.fonts import get_game_font
from graphics.camera import Camera
from simulation.planet import Planet
from simulation.rocket import Rocket


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    """Return the project font with Thai-capable fallbacks."""
    return get_game_font(size, bold=bold)


class UI:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font = get_font(16)
        self.font_small = get_font(14)

    def draw_hud(
        self,
        rocket: Rocket,
        camera: Camera,
        planet: Planet,
        orbit: Optional[Dict[str, Any]] = None,
        missions: Optional[Any] = None,
        paused: bool = False,
        notices: Optional[List[str]] = None,
    ) -> None:
        panel_x, panel_y = SCREEN_WIDTH - 280, 12
        lines = [
            ("Altitude", f"{rocket.altitude(planet.radius)/1000:.3f} km"),
            ("Speed", f"{rocket.speed():.1f} m/s"),
            ("Throttle", f"{rocket.throttle*100:.0f}%"),
            ("Thrust", f"{rocket.thrust/1000:.1f} kN"),
            ("Fuel", f"{rocket.fuel:.0f} kg"),
            ("Mass", f"{rocket.mass:.0f} kg"),
            ("Pitch", f"{rocket.angle:.0f} deg"),
        ]
        pygame.draw.rect(self.screen, (20, 24, 32), (panel_x - 8, panel_y - 8, 272, len(lines) * 22 + 34), border_radius=4)
        pygame.draw.rect(self.screen, (60, 70, 90), (panel_x - 8, panel_y - 8, 272, len(lines) * 22 + 34), 1, border_radius=4)
        for i, (label, value) in enumerate(lines):
            y = panel_y + i * 22
            self.screen.blit(self.font_small.render(f"{label}:", True, (140, 150, 170)), (panel_x, y))
            self.screen.blit(self.font.render(value, True, WHITE), (panel_x + 100, y))
        bar_y = panel_y + len(lines) * 22 + 8
        pygame.draw.rect(self.screen, (38, 44, 58), (panel_x, bar_y, 248, 12), border_radius=3)
        pygame.draw.rect(self.screen, YELLOW, (panel_x, bar_y, int(248 * rocket.throttle), 12), border_radius=3)
        if notices:
            for i, text in enumerate(notices[:3]):
                surf = self.font.render(text, True, YELLOW)
                rect = surf.get_rect(center=(SCREEN_WIDTH // 2, 16 + i * 34))
                pygame.draw.rect(self.screen, (24, 26, 32), rect.inflate(24, 12), border_radius=4)
                self.screen.blit(surf, rect)
        hint = self.font_small.render("W/S throttle | SPACE toggle | A/D pitch | P pause | R reset | ESC town", True, (190, 200, 216))
        pygame.draw.rect(self.screen, (16, 18, 24), hint.get_rect(topleft=(12, SCREEN_HEIGHT - 28)).inflate(16, 8), border_radius=3)
        self.screen.blit(hint, (12, SCREEN_HEIGHT - 28))
        if paused:
            surf = self.font.render("PAUSED", True, WHITE)
            self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))

    def draw_staging_info(self, rocket: Rocket) -> None:
        y = 120
        self.screen.blit(self.font.render("Stages / Parts", True, CYAN), (12, y))
        y += 24
        for part in rocket.parts:
            fuel = f" ({part.fuel_remaining:.0f} kg)" if part.part_type == "fuel_tank" else ""
            self.screen.blit(self.font_small.render(f"  {part.name} [{part.part_type}]{fuel}", True, WHITE), (12, y))
            y += 18
