"""Rocket parts, staging, and dynamics."""

from __future__ import annotations

import math
from typing import List, Optional

from maths.vector import Vec2


class Part:
    VALID_TYPES = ("fuel_tank", "engine", "command_pod", "wing", "leg")

    def __init__(
        self,
        name: str,
        mass: float,
        cost: float,
        part_type: str,
        fuel: float = 0.0,
        thrust: float = 0.0,
        isp: float = 0.0,
    ) -> None:
        self.name = name
        self.dry_mass = mass
        self.cost = cost
        self.part_type = part_type
        self.fuel_capacity = fuel
        self.fuel_remaining = fuel
        self.thrust = thrust
        self.isp = isp

    @property
    def mass(self) -> float:
        return self.dry_mass + self.fuel_remaining if self.part_type == "fuel_tank" else self.dry_mass


class Rocket:
    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.parts: List[Part] = []
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.throttle = 0.0
        self.angle = 0.0

    @property
    def position(self) -> Vec2:
        return Vec2(self.x, self.y)

    @property
    def velocity(self) -> Vec2:
        return Vec2(self.vx, self.vy)

    def add_part(self, part: Part) -> None:
        self.parts.append(part)

    def remove_part(self, index: int) -> Optional[Part]:
        if 0 <= index < len(self.parts):
            return self.parts.pop(index)
        return None

    def engines(self) -> List[Part]:
        return [p for p in self.parts if p.part_type == "engine"]

    def fuel_tanks(self) -> List[Part]:
        return [p for p in self.parts if p.part_type == "fuel_tank"]

    @property
    def max_thrust(self) -> float:
        return sum(engine.thrust for engine in self.engines())

    @property
    def thrust(self) -> float:
        return self.max_thrust * self.throttle

    @property
    def isp(self) -> float:
        engines = self.engines()
        total = sum(engine.thrust for engine in engines)
        if total <= 0:
            return 0.0
        return sum(engine.isp * engine.thrust for engine in engines) / total

    @property
    def fuel(self) -> float:
        return sum(tank.fuel_remaining for tank in self.fuel_tanks())

    @property
    def mass(self) -> float:
        return sum(part.mass for part in self.parts)

    def thrust_direction(self) -> Vec2:
        radial = Vec2(self.x, self.y).normalized()
        if radial.length() < 1e-6:
            radial = Vec2(1.0, 0.0)
        return radial.rotate(self.angle)

    def update(self, dt: float, planet_radius: float = 0.0) -> None:
        mass = self.mass
        if mass <= 0:
            return
        thrust_mag = self.thrust
        if thrust_mag > 0 and self.fuel > 0:
            direction = self.thrust_direction()
            self.vx += direction.x * thrust_mag / mass * dt
            self.vy += direction.y * thrust_mag / mass * dt
            if self.isp > 0:
                self._consume_fuel(thrust_mag / (self.isp * 9.80665) * dt)
        elif thrust_mag > 0 and self.fuel <= 0:
            self.throttle = 0.0

        self.x += self.vx * dt
        self.y += self.vy * dt

        r = math.hypot(self.x, self.y)
        if planet_radius > 0 and r < planet_radius:
            if r > 1e-6:
                scale = planet_radius / r
                self.x *= scale
                self.y *= scale
            else:
                self.x = planet_radius
                self.y = 0.0
            radial = Vec2(self.x, self.y).normalized()
            v_radial = self.vx * radial.x + self.vy * radial.y
            if v_radial < 0:
                self.vx -= v_radial * radial.x
                self.vy -= v_radial * radial.y

    def _consume_fuel(self, amount: float) -> None:
        left = amount
        for tank in self.fuel_tanks():
            if left <= 0:
                break
            take = min(tank.fuel_remaining, left)
            tank.fuel_remaining -= take
            left -= take

    def altitude(self, planet_radius: float) -> float:
        return math.hypot(self.x, self.y) - planet_radius

    def speed(self) -> float:
        return math.hypot(self.vx, self.vy)
