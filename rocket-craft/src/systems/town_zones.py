"""Town districts with music metadata."""

from __future__ import annotations

from typing import Dict, Tuple

ZoneId = str
Bounds = Tuple[int, int, int, int]

ZONES: Dict[ZoneId, dict] = {
    "hangar_area": {
        "name": "Hangar District",
        "bounds": (80, 570, 500, 330),
        "music": "town_hangar.mid",
        "color": (92, 96, 104),
    },
    "research_zone": {
        "name": "Research Ridge",
        "bounds": (1110, 250, 460, 320),
        "music": "town_research.mid",
        "color": (120, 170, 210),
    },
    "supply_zone": {
        "name": "Supply Yard",
        "bounds": (1080, 690, 470, 280),
        "music": "town_hangar.mid",
        "color": (156, 108, 64),
    },
    "mission_zone": {
        "name": "Mission Control",
        "bounds": (420, 230, 460, 300),
        "music": "town_research.mid",
        "color": (66, 128, 196),
    },
    "plaza": {
        "name": "Central Plaza",
        "bounds": (600, 500, 430, 330),
        "music": "town_plaza.mid",
        "color": (92, 150, 86),
    },
}

ZONE_ORDER = ("hangar_area", "research_zone", "supply_zone", "mission_zone", "plaza")


def get_zone_at(x: float, y: float) -> ZoneId:
    for zone_id in ZONE_ORDER:
        bx, by, bw, bh = ZONES[zone_id]["bounds"]
        if bx <= x <= bx + bw and by <= y <= by + bh:
            return zone_id
    return "plaza"
