"""2D vector math."""

from __future__ import annotations

from typing import Union

import numpy as np


Number = Union[int, float]


class Vec2:
    """Simple 2D vector."""

    __slots__ = ("x", "y")

    def __init__(self, x: Number = 0.0, y: Number = 0.0) -> None:
        self.x = float(x)
        self.y = float(y)

    def __add__(self, other: Vec2) -> Vec2:
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: Number) -> Vec2:
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: Number) -> Vec2:
        return self * scalar

    def __truediv__(self, scalar: Number) -> Vec2:
        return Vec2(self.x / scalar, self.y / scalar)

    def __neg__(self) -> Vec2:
        return Vec2(-self.x, -self.y)

    def __repr__(self) -> str:
        return f"Vec2({self.x:.4g}, {self.y:.4g})"

    def length(self) -> float:
        return float(np.hypot(self.x, self.y))

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y

    def normalized(self) -> Vec2:
        length = self.length()
        if length < 1e-12:
            return Vec2(0.0, 0.0)
        return self / length

    def dot(self, other: Vec2) -> float:
        return self.x * other.x + self.y * other.y

    def rotate(self, angle_degrees: float) -> Vec2:
        """Rotate vector counter-clockwise by angle in degrees."""
        rad = np.radians(angle_degrees)
        c, s = float(np.cos(rad)), float(np.sin(rad))
        return Vec2(self.x * c - self.y * s, self.x * s + self.y * c)

    def angle_degrees(self) -> float:
        return float(np.degrees(np.arctan2(self.y, self.x)))

    def copy(self) -> Vec2:
        return Vec2(self.x, self.y)

    @classmethod
    def from_polar(cls, length: float, angle_degrees: float) -> Vec2:
        rad = np.radians(angle_degrees)
        return cls(length * float(np.cos(rad)), length * float(np.sin(rad)))
