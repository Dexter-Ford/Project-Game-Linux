"""World rendering: planet, rocket, orbit prediction."""

from __future__ import annotations

import random
from typing import Optional

import pygame

from config import BLACK, CYAN, DARK_GRAY, GRAY, GREEN, ORANGE, WHITE, YELLOW
from graphics.camera import Camera
from graphics.sprites import RocketSpriteCache, sprite_rotation_degrees
from graphics.ui import get_font
from maths.kepler import predict_orbit_points
from maths.vector import Vec2
from simulation.planet import Planet
from simulation.rocket import Rocket


class Renderer:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font = get_font(14)
        self._rocket_sprites = RocketSpriteCache()
        rng = random.Random(7)
        w, h = screen.get_size()
        self.stars = [(rng.randrange(w), rng.randrange(h), rng.choice((90, 130, 180, 230))) for _ in range(140)]

    def clear(self, camera: Optional[Camera] = None) -> None:
        self.screen.fill(BLACK)
        for x, y, b in self.stars:
            self.screen.set_at((x, y), (b, b, min(255, b + 20)))

    def draw_planet(self, planet: Planet, camera: Camera) -> None:
        cx, cy = camera.world_to_screen(0.0, 0.0)
        radius = max(4, int(camera.world_length_to_pixels(planet.radius)))
        atm = int(camera.world_length_to_pixels(planet.radius + planet.atmosphere_height))
        if atm > 0:
            pygame.draw.circle(self.screen, (30, 60, 90), (cx, cy), atm, 1)
        pygame.draw.circle(self.screen, planet.color, (cx, cy), radius)
        if radius > 18:
            pygame.draw.circle(self.screen, (38, 110, 72), (cx - radius // 5, cy + radius // 6), radius // 4)
        pygame.draw.arc(self.screen, DARK_GRAY, (cx - radius, cy - radius, radius * 2, radius * 2), 0.5, 2.6, 2)

    def draw_launchpad(self, planet: Planet, camera: Camera) -> None:
        cx, cy = camera.world_to_screen(planet.radius, 0.0)
        pygame.draw.rect(self.screen, GRAY, (cx - 14, cy - 32, 18, 64))
        pygame.draw.line(self.screen, ORANGE, (cx, cy - 42), (cx + 70, cy - 42), 2)
        for x in range(cx, cx + 72, 24):
            pygame.draw.circle(self.screen, YELLOW, (x, cy - 42), 2)

    def draw_rocket(self, rocket: Rocket, camera: Camera) -> None:
        sx, sy = camera.world_to_screen(rocket.x, rocket.y)
        sprite = self._rocket_sprites.get(rocket, rocket.throttle > 0.01 and rocket.fuel > 0)
        scaled = pygame.transform.smoothscale(sprite, (32, 64))
        direction = rocket.thrust_direction()
        rotated = pygame.transform.rotate(scaled, -sprite_rotation_degrees(direction.x, direction.y))
        self.screen.blit(rotated, rotated.get_rect(center=(sx, sy)))

    def draw_velocity_vector(self, rocket: Rocket, camera: Camera) -> None:
        if rocket.speed() < 1:
            return
        direction = rocket.velocity.normalized()
        end = rocket.position + direction * min(250000.0, max(4000.0, rocket.speed() * 40.0))
        pygame.draw.line(self.screen, GREEN, camera.world_to_screen(rocket.x, rocket.y), camera.world_to_screen(end.x, end.y), 2)

    def draw_orbit(self, rocket: Rocket, camera: Camera, mu: float) -> None:
        points = predict_orbit_points(Vec2(rocket.x, rocket.y), Vec2(rocket.vx, rocket.vy), mu, num_points=96)
        if len(points) > 2:
            pygame.draw.aalines(self.screen, CYAN, True, [camera.world_to_screen(p.x, p.y) for p in points])
