"""Follow camera with altitude-based zoom."""

from __future__ import annotations

from typing import Optional

from config import SCREEN_HEIGHT, SCREEN_WIDTH
from simulation.planet import Planet
from simulation.rocket import Rocket


class Camera:
    def __init__(self) -> None:
        self.x = 0.0
        self.y = 0.0
        self.zoom = 1 / 500.0

    def follow(self, rocket: Rocket, planet: Optional[Planet] = None) -> None:
        self.x = rocket.x
        self.y = rocket.y

    def set_zoom_from_altitude(self, altitude: float) -> None:
        km = max(0.0, altitude / 1000.0)
        self.zoom = 1.0 / (500.0 * (1.0 + km / 10.0))

    def world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        sx = SCREEN_WIDTH / 2 + (wx - self.x) * self.zoom
        sy = SCREEN_HEIGHT / 2 - (wy - self.y) * self.zoom
        return int(sx), int(sy)

    def world_length_to_pixels(self, length_m: float) -> float:
        return length_m * self.zoom
