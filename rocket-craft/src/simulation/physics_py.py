"""Pure-Python patched-conics physics."""

from __future__ import annotations

import math
from typing import List, Optional

from config import DRAG_COEFFICIENT, G, ROCKET_CROSS_SECTION
from simulation.planet import Planet
from simulation.rocket import Rocket


class GravitySimulator:
    BACKEND = "python"

    def __init__(self, primary: Planet, secondary_bodies: Optional[List[Planet]] = None) -> None:
        self.primary = primary
        self.bodies = [primary] + list(secondary_bodies or [])
        self.active_body = primary

    def apply_gravity(self, rocket: Rocket, dt: float) -> None:
        r = math.hypot(rocket.x, rocket.y)
        if r < 1.0 or rocket.mass <= 0:
            return
        accel = G * self.active_body.mass / (r * r)
        rocket.vx += -accel * rocket.x / r * dt
        rocket.vy += -accel * rocket.y / r * dt

    def apply_drag(self, rocket: Rocket, dt: float) -> None:
        rho = self.active_body.atmosphere_density(self.active_body.altitude(rocket.x, rocket.y))
        speed = math.hypot(rocket.vx, rocket.vy)
        if rho <= 0 or speed < 0.1 or rocket.mass <= 0:
            return
        force = 0.5 * rho * speed * speed * DRAG_COEFFICIENT * ROCKET_CROSS_SECTION
        accel = force / rocket.mass
        rocket.vx -= accel * rocket.vx / speed * dt
        rocket.vy -= accel * rocket.vy / speed * dt

    def check_soi_transition(self, rocket: Rocket) -> None:
        return
