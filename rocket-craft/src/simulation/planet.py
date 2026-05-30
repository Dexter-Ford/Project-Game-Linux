"""Planet and atmosphere model."""

from __future__ import annotations

import math
from typing import Tuple

from config import G


class Planet:
    def __init__(
        self,
        name: str,
        mass: float,
        radius: float,
        soi_radius: float,
        atmosphere_height: float,
        color: Tuple[int, int, int] = (50, 160, 80),
    ) -> None:
        self.name = name
        self.mass = mass
        self.radius = radius
        self.soi_radius = soi_radius
        self.atmosphere_height = atmosphere_height
        self.color = color
        self.mu = G * mass

    def altitude(self, x: float, y: float) -> float:
        return math.hypot(x, y) - self.radius

    def atmosphere_density(self, altitude: float) -> float:
        if altitude < 0 or self.atmosphere_height <= 0 or altitude > self.atmosphere_height * 3:
            return 0.0
        return 1.225 * math.exp(-altitude / (self.atmosphere_height / 5.0))
