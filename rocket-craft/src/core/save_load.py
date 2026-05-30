"""JSON save/load system for RocketCraft."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class SaveManager:
    """Persist lightweight campaign data to JSON files."""

    def __init__(self, save_dir: str = "saves") -> None:
        root = Path(__file__).resolve().parents[2]
        path = Path(save_dir)
        self.save_dir = str(path if path.is_absolute() else root / path)
        os.makedirs(self.save_dir, exist_ok=True)
        self.current_save_slot: str = "autosave"

    def save(self, filename: str, game_data: Dict[str, Any]) -> str:
        """Save game state and return the path written."""
        data = {
            "version": "0.1.0",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "money": game_data.get("money", 50_000),
            "day": game_data.get("day", 1),
            "hour": game_data.get("hour", 6),
            "minute": game_data.get("minute", 0.0),
            "time_speed": game_data.get("time_speed", 1.0),
            "day_length_seconds": game_data.get("day_length_seconds", 600.0),
            "unlocked_parts": game_data.get("unlocked_parts", []),
            "rocket_config": game_data.get("rocket_config", []),
            "completed_contracts": game_data.get("completed_contracts", []),
            "reputation": game_data.get("reputation", 0),
            "research_points": game_data.get("research_points", 0),
            "story_completed_events": game_data.get("story_completed_events", []),
            "story_choices": game_data.get("story_choices", {}),
            "story_flags": game_data.get("story_flags", {}),
            "npc_morale": game_data.get("npc_morale", {}),
            "npc_positions": game_data.get("npc_positions", {}),
            "npc_memory": game_data.get("npc_memory", {}),
            "seen_town_intro": game_data.get("seen_town_intro", False),
            "player_name": game_data.get("player_name", "Director"),
            "player_gender": game_data.get("player_gender", "unspecified"),
            "player_color": game_data.get("player_color", [255, 236, 39]),
            "home_decor_style": game_data.get("home_decor_style", "cozy"),
            "mailbox": game_data.get("mailbox", []),
            "inventory": game_data.get("inventory", []),
            "completed_deep_dialogues": game_data.get("completed_deep_dialogues", []),
            "deep_dialogue_progress": game_data.get("deep_dialogue_progress", {}),
            "lore_unlocked": game_data.get("lore_unlocked", []),
        }
        data["seen_intro"] = game_data.get("seen_intro", self.has_seen_intro())
        data["has_seen_intro"] = game_data.get("has_seen_intro", data["seen_intro"])
        safe_name = filename.replace("/", "_").replace("\\", "_")
        path = os.path.join(self.save_dir, f"{safe_name}.json")
        with open(path, "w", encoding="utf-8") as save_file:
            json.dump(data, save_file, indent=2)
        return path

    def load(self, filename: str) -> Dict[str, Any]:
        """Load game state from a JSON file."""
        path = os.path.join(self.save_dir, filename)
        if not path.endswith(".json"):
            path += ".json"
        with open(path, "r", encoding="utf-8") as save_file:
            return json.load(save_file)

    def get_saves(self) -> List[Dict[str, Any]]:
        """List all save summaries, newest first."""
        saves: List[Dict[str, Any]] = []
        if not os.path.isdir(self.save_dir):
            return saves

        for filename in os.listdir(self.save_dir):
            if not filename.endswith(".json") or filename == "profile.json":
                continue
            path = os.path.join(self.save_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as save_file:
                    data = json.load(save_file)
            except (OSError, json.JSONDecodeError):
                continue
            saves.append(
                {
                    "filename": filename,
                    "date": data.get("timestamp", ""),
                    "player_name": data.get("player_name", "Director"),
                    "day": data.get("day", 1),
                    "money": data.get("money", 0),
                    "reputation": data.get("reputation", 0),
                    "has_seen_intro": bool(data.get("has_seen_intro", data.get("seen_intro", False))),
                }
            )

        return sorted(saves, key=lambda item: item["date"], reverse=True)

    def _profile_path(self) -> str:
        return os.path.join(self.save_dir, "profile.json")

    def _load_profile(self) -> Dict[str, Any]:
        try:
            with open(self._profile_path(), "r", encoding="utf-8") as profile_file:
                return json.load(profile_file)
        except (OSError, json.JSONDecodeError):
            return {}

    def has_seen_intro(self, filename: str = "") -> bool:
        """Return whether the one-time opening cutscene has already played."""
        if filename:
            try:
                data = self.load(filename)
            except OSError:
                data = {}
            if data:
                return bool(data.get("has_seen_intro", data.get("seen_intro", False)))
        return bool(self._load_profile().get("seen_intro", False))

    def set_intro_seen(self) -> None:
        """Persist the one-time opening cutscene flag."""
        profile = self._load_profile()
        profile["seen_intro"] = True
        profile["timestamp"] = datetime.now().isoformat(timespec="seconds")
        with open(self._profile_path(), "w", encoding="utf-8") as profile_file:
            json.dump(profile, profile_file, indent=2)

    def set_current_slot(self, filename: str) -> None:
        """Remember which save file is active (with or without .json)."""
        safe = filename.replace("/", "_").replace("\\", "_")
        self.current_save_slot = safe.replace(".json", "") or "autosave"

    def bed_save(self, game_data: Dict[str, Any]) -> str:
        """Save at the bed — overwrites current save slot or the most recent save."""
        slot = self.current_save_slot
        if not slot:
            saves = self.get_saves()
            if saves:
                slot = saves[0]["filename"].replace(".json", "")
            else:
                slot = "save_01"
        return self.save(slot, game_data)
