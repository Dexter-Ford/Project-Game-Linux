"""Launch/orbit flight screen."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Tuple

import pygame

from config import EARTH, GREEN, KEY_ROTATE_FINE, PHYSICS_STEP, THROTTLE_CHANGE_RATE
from entities.parts import build_rocket_from_parts, is_launchable
from graphics.camera import Camera
from graphics.renderer import Renderer
from graphics.ui import UI
from maths.kepler import orbital_elements_from_state
from maths.vector import Vec2
from simulation.mission import MissionTracker
from simulation.physics import GravitySimulator
from simulation.planet import Planet
from simulation.rocket import Part, Rocket

if TYPE_CHECKING:
    from audio.audio_manager import AudioManager
    from core.game_session import GameSession

Notice = Tuple[str, float]


def create_earth() -> Planet:
    return Planet(
        name=EARTH["name"],
        mass=EARTH["mass"],
        radius=EARTH["radius"],
        soi_radius=EARTH["soi_radius"],
        atmosphere_height=EARTH["atmosphere_height"],
        color=GREEN,
    )


def build_starter_rocket(planet: Planet) -> Rocket:
    rocket = Rocket(x=planet.radius, y=0.0)
    rocket.add_part(Part("Command Pod", mass=800, cost=5000, part_type="command_pod"))
    rocket.add_part(Part("Fuel Tank", mass=500, cost=2000, part_type="fuel_tank", fuel=5000))
    rocket.add_part(
        Part("Engine", mass=300, cost=3000, part_type="engine", thrust=200e3, isp=300)
    )
    return rocket


class LaunchScreen:
    """Fixed-timestep launch simulation screen."""

    def __init__(
        self,
        screen: pygame.Surface,
        audio: "AudioManager | None" = None,
        session: "GameSession | None" = None,
        auto_ignite: bool = False,
    ) -> None:
        self.screen = screen
        self.audio = audio
        self.session = session
        self.earth = create_earth()
        self.physics = GravitySimulator(self.earth)
        self.camera = Camera()
        self.renderer = Renderer(screen)
        self.ui = UI(screen)
        self.missions = MissionTracker()
        self.accumulator = 0.0
        self.paused = False
        self.rotate_left = False
        self.rotate_right = False
        self.throttle_up = False
        self.throttle_down = False
        self.notices: List[Notice] = [("Launch Day", 2.0)]
        self._thrust_playing = False

        keys = session.rocket_part_keys if session and session.rocket_part_keys else []
        if keys and is_launchable(keys):
            self.rocket = build_rocket_from_parts(self.earth.radius, keys)
        else:
            self.rocket = build_starter_rocket(self.earth)

        if auto_ignite:
            self.rocket.throttle = 1.0
            self._start_thrust_audio()

    def _start_thrust_audio(self) -> None:
        if self.audio is not None and self.rocket.throttle > 0.05:
            self.audio.play_sfx("thrust", loop=True, volume=0.6)
            self._thrust_playing = True

    def _stop_thrust_audio(self) -> None:
        if self.audio is not None:
            self.audio.stop_sfx("thrust")
        self._thrust_playing = False

    def reset_flight(self) -> None:
        keys = self.session.rocket_part_keys if self.session else []
        if keys and is_launchable(keys):
            self.rocket = build_rocket_from_parts(self.earth.radius, keys)
        else:
            self.rocket = build_starter_rocket(self.earth)
        self.physics.active_body = self.earth
        self.missions.reset()
        self.notices = [("Flight reset", 1.2)]
        self.accumulator = 0.0
        self._stop_thrust_audio()

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._stop_thrust_audio()
                return "town"
            if event.key == pygame.K_SPACE:
                self.rocket.throttle = 1.0 if self.rocket.throttle < 0.5 else 0.0
                if self.rocket.throttle > 0.5:
                    self._start_thrust_audio()
                else:
                    self._stop_thrust_audio()
            elif event.key == pygame.K_w:
                self.throttle_up = True
            elif event.key == pygame.K_s:
                self.throttle_down = True
            elif event.key == pygame.K_a:
                self.rotate_left = True
            elif event.key == pygame.K_d:
                self.rotate_right = True
            elif event.key == pygame.K_p:
                self.paused = not self.paused
                self.accumulator = 0.0
            elif event.key == pygame.K_r:
                self.reset_flight()
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_w:
                self.throttle_up = False
            elif event.key == pygame.K_s:
                self.throttle_down = False
            elif event.key == pygame.K_a:
                self.rotate_left = False
            elif event.key == pygame.K_d:
                self.rotate_right = False
        return None

    def update(self, dt: float) -> None:
        if not self.paused:
            self.accumulator += dt

        if self.throttle_up and not self.paused:
            self.rocket.throttle = min(1.0, self.rocket.throttle + THROTTLE_CHANGE_RATE * dt)
        if self.throttle_down and not self.paused:
            self.rocket.throttle = max(0.0, self.rocket.throttle - THROTTLE_CHANGE_RATE * dt)

        if self.rocket.throttle > 0.05 and not self._thrust_playing:
            self._start_thrust_audio()
        elif self.rocket.throttle <= 0.05 and self._thrust_playing:
            self._stop_thrust_audio()

        if self.audio is not None:
            self.audio.update_launch_audio(self.rocket.throttle)

        if self.rotate_left and not self.paused:
            self.rocket.angle -= KEY_ROTATE_FINE * dt * 10.0
        if self.rotate_right and not self.paused:
            self.rocket.angle += KEY_ROTATE_FINE * dt * 10.0
        if self.rocket.angle > 180.0 or self.rocket.angle < -180.0:
            self.rocket.angle = ((self.rocket.angle + 180.0) % 360.0) - 180.0

        while not self.paused and self.accumulator >= PHYSICS_STEP:
            self.physics.apply_gravity(self.rocket, PHYSICS_STEP)
            self.physics.apply_drag(self.rocket, PHYSICS_STEP)
            self.physics.check_soi_transition(self.rocket)
            self.rocket.update(PHYSICS_STEP, planet_radius=self.physics.active_body.radius)
            self.accumulator -= PHYSICS_STEP

        orbit = self._orbit()
        if not self.paused:
            for mission in self.missions.update(self.rocket, self.physics.active_body, orbit):
                self.notices.append((f"Mission complete: {mission.name} +${mission.reward}", 3.5))
                if self.session is not None:
                    self.session.money += mission.reward
                    if mission.name not in self.session.completed_contracts:
                        self.session.completed_contracts.append(mission.name)

        self.notices = [(text, time_left - dt) for text, time_left in self.notices if time_left > 0.0]

    def draw(self, screen: Optional[pygame.Surface] = None) -> None:
        altitude = self.rocket.altitude(self.earth.radius)
        self.camera.follow(self.rocket, self.earth)
        self.camera.set_zoom_from_altitude(altitude)

        orbit = self._orbit()
        self.renderer.clear()
        self.renderer.draw_planet(self.earth, self.camera)
        self.renderer.draw_launchpad(self.earth, self.camera)
        self.renderer.draw_orbit(self.rocket, self.camera, self.physics.active_body.mu)
        self.renderer.draw_velocity_vector(self.rocket, self.camera)
        self.renderer.draw_rocket(self.rocket, self.camera)
        self.ui.draw_staging_info(self.rocket)
        self.ui.draw_hud(
            self.rocket,
            self.camera,
            self.earth,
            orbit,
            self.missions,
            self.paused,
            [text for text, _ in self.notices],
        )

    def _orbit(self) -> dict:
        return orbital_elements_from_state(
            Vec2(self.rocket.x, self.rocket.y),
            Vec2(self.rocket.vx, self.rocket.vy),
            self.physics.active_body.mu,
            self.physics.active_body.radius,
        )
