"""Simple milestone missions for prototype gameplay."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Union

from simulation.planet import Planet
from simulation.rocket import Rocket


OrbitInfo = Dict[str, Union[float, bool]]
MissionCondition = Callable[[Rocket, Planet, float, float, OrbitInfo], bool]


@dataclass
class Mission:
    name: str
    description: str
    reward: int
    condition: MissionCondition
    completed: bool = False


class MissionTracker:
    """Tracks one-flight milestones and reward funds."""

    def __init__(self) -> None:
        self.funds = 0
        self.missions: List[Mission] = [
            Mission(
                "Liftoff",
                "Leave the launch pad",
                1_000,
                lambda rocket, planet, alt, speed, orbit: alt > 5.0 and speed > 1.0,
            ),
            Mission(
                "Tower Clear",
                "Climb past 100 m",
                1_500,
                lambda rocket, planet, alt, speed, orbit: alt >= 100.0,
            ),
            Mission(
                "Mach 1",
                "Break the sound barrier",
                3_000,
                lambda rocket, planet, alt, speed, orbit: speed >= 343.0,
            ),
            Mission(
                "Thin Air",
                "Reach 10 km altitude",
                5_000,
                lambda rocket, planet, alt, speed, orbit: alt >= 10_000.0,
            ),
            Mission(
                "Space",
                "Cross the atmosphere",
                15_000,
                lambda rocket, planet, alt, speed, orbit: alt >= planet.atmosphere_height,
            ),
            Mission(
                "Orbit",
                "Periapsis above air",
                50_000,
                lambda rocket, planet, alt, speed, orbit: bool(orbit.get("bound"))
                and float(orbit.get("periapsis_altitude", -1.0)) > planet.atmosphere_height,
            ),
        ]

    def reset(self) -> None:
        self.funds = 0
        for mission in self.missions:
            mission.completed = False

    def update(
        self,
        rocket: Rocket,
        planet: Planet,
        orbit: OrbitInfo,
    ) -> List[Mission]:
        altitude = rocket.altitude(planet.radius)
        speed = rocket.speed()
        completed_now: List[Mission] = []

        for mission in self.missions:
            if mission.completed:
                continue
            if mission.condition(rocket, planet, altitude, speed, orbit):
                mission.completed = True
                self.funds += mission.reward
                completed_now.append(mission)

        return completed_now

    def visible_missions(self, count: int = 5) -> List[Mission]:
        active = [mission for mission in self.missions if not mission.completed][:count]
        done = [mission for mission in self.missions if mission.completed]
        slots = max(0, count - len(active))
        return active + (done[-slots:] if slots else [])
