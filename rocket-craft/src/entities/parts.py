"""Rocket part catalog for the hangar."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from simulation.rocket import Part, Rocket


@dataclass(frozen=True)
class RocketPart:
    key: str
    name: str
    part_type: str
    mass: float
    cost: float
    thrust: float = 0.0
    isp: float = 0.0
    fuel: float = 0.0

    def to_sim_part(self) -> Part:
        return Part(self.name, self.mass, self.cost, self.part_type, self.fuel, self.thrust, self.isp)


PARTS_CATALOG: Dict[str, RocketPart] = {
    "basic_pod": RocketPart("basic_pod", "Command Pod", "command_pod", 500, 5000),
    "small_tank": RocketPart("small_tank", "Small Fuel Tank", "fuel_tank", 300, 2000, fuel=500),
    "medium_tank": RocketPart("medium_tank", "Medium Fuel Tank", "fuel_tank", 600, 4000, fuel=1200),
    "basic_engine": RocketPart("basic_engine", "Basic Engine", "engine", 200, 8000, thrust=150e3, isp=280),
    "advanced_engine": RocketPart("advanced_engine", "Advanced Engine", "engine", 280, 14000, thrust=220e3, isp=310),
    "small_wing": RocketPart("small_wing", "Small Fin", "wing", 50, 500),
    "landing_leg": RocketPart("landing_leg", "Landing Leg", "leg", 100, 1000),
    "salvaged_valve": RocketPart(
        "salvaged_valve",
        "Salvaged Valve",
        "engine",
        160,
        4500,
        thrust=130e3,
        isp=292,
    ),
    "firefly_engine": RocketPart(
        "firefly_engine",
        "Firefly Engine",
        "engine",
        200,
        6200,
        thrust=195e3,
        isp=335,
    ),
}


def is_launchable(part_keys: List[str]) -> bool:
    types = {PARTS_CATALOG[k].part_type for k in part_keys if k in PARTS_CATALOG}
    return {"command_pod", "engine", "fuel_tank"}.issubset(types)


def total_mass(part_keys: List[str]) -> float:
    return sum(PARTS_CATALOG[k].mass + PARTS_CATALOG[k].fuel for k in part_keys if k in PARTS_CATALOG)


def total_cost(part_keys: List[str]) -> float:
    return sum(PARTS_CATALOG[k].cost for k in part_keys if k in PARTS_CATALOG)


def build_rocket_from_parts(planet_radius: float, part_keys: List[str]) -> Rocket:
    rocket = Rocket(x=planet_radius, y=0.0)
    for key in part_keys:
        part = PARTS_CATALOG.get(key)
        if part:
            rocket.add_part(part.to_sim_part())
    return rocket
