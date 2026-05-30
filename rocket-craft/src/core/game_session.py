"""Shared campaign state across screens."""

from __future__ import annotations

from typing import Any, Dict, List

from config import STARTING_FUNDS
from core.time_system import TimeSystem
from entities.parts import PARTS_CATALOG

_QUEST_PARTS = frozenset({"salvaged_valve", "firefly_engine"})


def default_unlocked_parts() -> List[str]:
    return [key for key in PARTS_CATALOG if key not in _QUEST_PARTS]


class GameSession:
    def __init__(self) -> None:
        self.reset_new_game()

    def reset_new_game(self) -> None:
        self.money = STARTING_FUNDS
        self.time = TimeSystem(day=1, hour=6, minute=0.0)
        self.rocket_part_keys: List[str] = []
        self.seen_town_intro = False
        self.npc_positions: Dict[str, List[float]] = {}
        self.npc_memory: Dict[str, Dict[str, Any]] = {}
        self.completed_contracts: List[str] = []
        self.unlocked_parts: List[str] = default_unlocked_parts()
        self.reputation = 0
        self.research_points = 0
        self.story_completed_events: List[str] = []
        self.story_choices: Dict[str, int] = {}
        self.story_flags: Dict[str, Any] = {}
        self.npc_morale: Dict[str, int] = {
            "dr_chen": 5,
            "bob": 5,
            "maria": 5,
            "jenkins": 5,
        }
        self.player_name = "Director"
        self.player_gender = "unspecified"
        self.player_color = (255, 236, 39)
        self.home_decor_style = "cozy"
        self.mailbox: List[Dict[str, Any]] = []
        self.inventory: List[str] = []
        self.completed_deep_dialogues: List[str] = []
        self.deep_dialogue_progress: Dict[str, Dict[str, Any]] = {}
        self.lore_unlocked: List[str] = []

    def to_save_dict(self) -> Dict[str, Any]:
        return {
            "money": self.money,
            "day": self.time.day,
            "hour": self.time.hour,
            "minute": self.time.minute,
            "time_speed": self.time.time_speed,
            "day_length_seconds": self.time.day_length_seconds,
            "rocket_config": list(self.rocket_part_keys),
            "seen_town_intro": self.seen_town_intro,
            "npc_positions": dict(self.npc_positions),
            "npc_memory": dict(self.npc_memory),
            "completed_contracts": list(self.completed_contracts),
            "unlocked_parts": list(self.unlocked_parts),
            "reputation": self.reputation,
            "research_points": self.research_points,
            "story_completed_events": list(self.story_completed_events),
            "story_choices": dict(self.story_choices),
            "story_flags": dict(self.story_flags),
            "npc_morale": dict(self.npc_morale),
            "player_name": self.player_name,
            "player_gender": self.player_gender,
            "player_color": list(self.player_color),
            "home_decor_style": self.home_decor_style,
            "mailbox": list(self.mailbox),
            "inventory": list(self.inventory),
            "completed_deep_dialogues": list(self.completed_deep_dialogues),
            "deep_dialogue_progress": dict(self.deep_dialogue_progress),
            "lore_unlocked": list(self.lore_unlocked),
        }

    def apply_save(self, data: Dict[str, Any]) -> None:
        self.money = int(data.get("money", STARTING_FUNDS))
        self.time = TimeSystem.from_dict(data)
        self.rocket_part_keys = list(data.get("rocket_config", []))
        self.seen_town_intro = bool(data.get("seen_town_intro", False))
        self.npc_positions = dict(data.get("npc_positions", {}))
        self.npc_memory = dict(data.get("npc_memory", {}))
        self.completed_contracts = list(data.get("completed_contracts", []))
        self.unlocked_parts = list(data.get("unlocked_parts", default_unlocked_parts()))
        self.reputation = int(data.get("reputation", 0))
        self.research_points = int(data.get("research_points", 0))
        self.story_completed_events = list(data.get("story_completed_events", []))
        self.story_choices = dict(data.get("story_choices", {}))
        self.story_flags = dict(data.get("story_flags", {}))
        default_morale = {"dr_chen": 5, "bob": 5, "maria": 5, "jenkins": 5}
        default_morale.update({str(k): int(v) for k, v in dict(data.get("npc_morale", {})).items()})
        self.npc_morale = {key: max(0, min(10, value)) for key, value in default_morale.items()}
        self.player_name = str(data.get("player_name", "Director"))[:20] or "Director"
        self.player_gender = str(data.get("player_gender", "unspecified"))
        self.home_decor_style = str(data.get("home_decor_style", "cozy"))
        self.mailbox = list(data.get("mailbox", []))
        self.inventory = list(data.get("inventory", []))
        self.completed_deep_dialogues = list(data.get("completed_deep_dialogues", []))
        self.deep_dialogue_progress = dict(data.get("deep_dialogue_progress", {}))
        self.lore_unlocked = list(data.get("lore_unlocked", []))
        color = data.get("player_color", (255, 236, 39))
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            self.player_color = tuple(int(max(0, min(255, c))) for c in color[:3])
        else:
            self.player_color = (255, 236, 39)
