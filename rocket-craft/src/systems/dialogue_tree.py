"""Branching NPC dialogue trees with rewards and save-backed progress."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

Choice = Tuple[str, str]


class DialogueTree:
    """Walk a single NPC conversation tree loaded from JSON."""

    def __init__(self, tree_id: str, tree_data: Dict[str, Any], start_node: str = "start") -> None:
        self.tree_id = tree_id
        self.nodes: Dict[str, Dict[str, Any]] = dict(tree_data.get("nodes", {}))
        self.current_node = start_node if start_node in self.nodes else "start"
        self.history: List[str] = []

    def get_current_text(self) -> str:
        return str(self.nodes.get(self.current_node, {}).get("text", ""))

    def get_speaker(self) -> str:
        return str(self.nodes.get(self.current_node, {}).get("speaker", ""))

    def get_choices(self) -> List[Choice]:
        raw = self.nodes.get(self.current_node, {}).get("choices", [])
        result: List[Choice] = []
        for item in raw:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                result.append((str(item[0]), str(item[1])))
        return result

    def choose(self, choice_index: int) -> bool:
        choices = self.get_choices()
        if 0 <= choice_index < len(choices):
            _label, next_node = choices[choice_index]
            self.history.append(self.current_node)
            if next_node in self.nodes:
                self.current_node = next_node
            else:
                self.current_node = next_node
            return True
        return False

    def jump_to(self, node_id: str) -> None:
        if node_id in self.nodes:
            self.history.append(self.current_node)
            self.current_node = node_id

    def is_end(self) -> bool:
        return len(self.get_choices()) == 0

    def get_rewards(self) -> Dict[str, Any]:
        return dict(self.nodes.get(self.current_node, {}).get("rewards", {}))

    def branch_targets_from_start(self) -> List[str]:
        start = self.nodes.get("start", {})
        targets: List[str] = []
        for item in start.get("choices", []):
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                targets.append(str(item[1]))
        return targets


def load_dialogue_trees(path: Optional[Path] = None) -> Dict[str, Any]:
    if path is None:
        path = Path(__file__).resolve().parents[1] / "data" / "dialogue_trees.json"
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


NPC_TREE_IDS = {
    "Dr. Chen": "dr_chen_resign",
    "Bob": "bob_engine",
    "Maria": "maria_abort",
    "Old Man Jenkins": "jenkins_firefly",
}

NPC_DISPLAY_NAMES = {
    "Dr. Chen": "Dr. Chen",
    "Bob": "Bob",
    "Maria": "Maria",
    "Old Man Jenkins": "Old Man Jenkins",
}


def resolve_tree_id(npc_name: str, session: Any) -> Optional[str]:
    """Pick which tree to run for this NPC (including cross-NPC quests)."""
    inventory = list(getattr(session, "inventory", []))
    unlocked = set(getattr(session, "unlocked_parts", []))
    completed = set(getattr(session, "completed_deep_dialogues", []))

    if npc_name == "Bob":
        if "antique_fuel_valve" in inventory and "firefly_engine" not in unlocked:
            if "bob_valve" not in completed:
                return "bob_valve"
        if "bob_engine" not in completed:
            return "bob_engine"
        return None

    tree_id = NPC_TREE_IDS.get(npc_name)
    if tree_id and tree_id not in completed:
        return tree_id
    return None


def apply_dialogue_rewards(session: Any, rewards: Dict[str, Any]) -> List[str]:
    """Apply reward dict from a dialogue leaf; return player-facing notices."""
    notices: List[str] = []
    if not rewards:
        return notices

    for key, value in rewards.items():
        if key.endswith("_morale"):
            npc_key = key.replace("_morale", "")
            if npc_key == "old_man_jenkins":
                npc_key = "jenkins"
            current = int(session.npc_morale.get(npc_key, 5))
            session.npc_morale[npc_key] = max(0, min(10, current + int(value)))
            continue

        if key == "research_points":
            session.research_points = int(session.research_points) + int(value)
            notices.append(f"+{value} research points")
            continue

        if key == "reputation":
            session.reputation = int(session.reputation) + int(value)
            continue

        if key == "money":
            session.money = int(session.money) + int(value)
            notices.append(f"Funds changed by ${int(value):,}")

        if key == "item":
            item_id = str(value)
            if item_id not in session.inventory:
                session.inventory.append(item_id)
                notices.append(f"Received: {item_id.replace('_', ' ').title()}")

        if key == "remove_item":
            item_id = str(value)
            while item_id in session.inventory:
                session.inventory.remove(item_id)

        if key == "unlock_part":
            part_key = str(value)
            if part_key not in session.unlocked_parts:
                session.unlocked_parts.append(part_key)
                notices.append(f"Hangar unlocked: {part_key.replace('_', ' ').title()}")
            if part_key == "firefly_engine" and "bob_valve" not in session.completed_deep_dialogues:
                session.completed_deep_dialogues.append("bob_valve")

        if key == "unlock_dialogue":
            session.story_flags[str(value)] = True

        if key == "lore":
            lore_id = str(value)
            if lore_id not in session.lore_unlocked:
                session.lore_unlocked.append(lore_id)
                notices.append("New lore recorded")

        if key == "research_boost":
            session.story_flags[f"research_{value}"] = True

        if key == "skill":
            session.story_flags[f"skill_{value}"] = True

        if key == "respect":
            session.story_flags[f"respect_{value}"] = True

    return notices
