"""UI controller for branching deep NPC dialogues."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pygame

from core.fonts import get_dialogue_font, get_game_font
from core.game_session import GameSession
from graphics.dialogue_box import DialogueBox as ScrollDialogueBox
from systems.dialogue_tree import (
    DialogueTree,
    NPC_DISPLAY_NAMES,
    apply_dialogue_rewards,
    load_dialogue_trees,
    resolve_tree_id,
)


class DeepDialogueController:
    """Runs one dialogue tree with scroll UI, branch tracking, and rewards."""

    def __init__(self, session: GameSession) -> None:
        self.session = session
        self.trees_data = load_dialogue_trees()
        self.active = False
        self.npc_name = ""
        self.tree_id = ""
        self.tree: Optional[DialogueTree] = None
        self.box: Optional[ScrollDialogueBox] = None
        self.pending_notices: List[str] = []
        self._font_body = get_dialogue_font(22)
        self._font_hint = get_game_font(14)

    def should_use_deep(self, npc_name: str) -> bool:
        return resolve_tree_id(npc_name, self.session) is not None

    def open(self, npc_name: str, screen: Optional[pygame.Surface] = None) -> None:
        tree_id = resolve_tree_id(npc_name, self.session)
        if tree_id is None or tree_id not in self.trees_data:
            self.active = False
            return

        self.npc_name = npc_name
        self.tree_id = tree_id
        tree_blob = self.trees_data[tree_id]
        progress = self._progress(tree_id)
        start_node = str(progress.get("current_node", "start"))
        self.tree = DialogueTree(tree_id, tree_blob, start_node=start_node)
        self.active = True
        self.pending_notices = []
        if screen is not None:
            self.box = ScrollDialogueBox(screen, self._font_body)
        else:
            self.box = None
        self._sync_display()

    def close(self) -> None:
        self.active = False
        self.tree = None
        if self.box is not None:
            self.box.hide()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.active or self.tree is None:
            return False

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._save_progress()
            self.close()
            return True

        payload = None
        if self.box is not None:
            payload = self.box.handle_event(event)

        if payload is not None:
            if isinstance(payload, dict) and payload.get("close"):
                self._save_progress()
                self._check_tree_complete()
                self.close()
                return True
            if isinstance(payload, dict) and payload.get("action") == "more_topics":
                self.tree.jump_to("start")
                self._sync_display()
                return True
            if isinstance(payload, dict) and payload.get("action") == "end_talk":
                self._save_progress()
                self._check_tree_complete()
                self.close()
                return True
            if isinstance(payload, int):
                self._choose_index(payload)
                return True

        if event.type == pygame.KEYDOWN and pygame.K_1 <= event.key <= pygame.K_9:
            index = event.key - pygame.K_1
            self._choose_index(index)
            return True

        return True

    def _choose_index(self, index: int) -> None:
        if self.tree is None:
            return
        choices = self._filtered_choices()
        if not (0 <= index < len(choices)):
            return
        _label, next_id = choices[index]
        self.tree.history.append(self.tree.current_node)
        if next_id in self.tree.nodes:
            self.tree.current_node = next_id

        self._mark_visited(self.tree.current_node)
        rewards = self.tree.get_rewards()
        if rewards:
            self.pending_notices.extend(apply_dialogue_rewards(self.session, rewards))
            self._mark_branch_complete(self.tree.current_node)

        self._save_progress()
        self._sync_display()

    def _filtered_choices(self) -> List[Tuple[str, str]]:
        if self.tree is None:
            return []
        if self.tree.current_node != "start":
            return self.tree.get_choices()

        completed = set(self._progress(self.tree_id).get("completed_branches", []))
        return [(label, node_id) for label, node_id in self.tree.get_choices() if node_id not in completed]

    def _sync_display(self) -> None:
        if self.tree is None or self.box is None:
            return

        speaker = self.tree.get_speaker() or NPC_DISPLAY_NAMES.get(self.npc_name, self.npc_name)
        text = self.tree.get_current_text()
        if self.pending_notices:
            text = text + "\n\n[" + " | ".join(self.pending_notices) + "]"
            self.pending_notices = []

        if self.tree.is_end() or not self._filtered_choices():
            extra = self._end_of_branch_choices()
            choices = [(label, payload) for label, payload in extra]
            self.box.show(speaker, text, choices)
            return

        choices = [(f"{label}", idx) for idx, (label, _nid) in enumerate(self._filtered_choices())]
        self.box.show(speaker, text, choices)

    def _end_of_branch_choices(self) -> List[Tuple[str, object]]:
        if self.tree is None:
            return [("End conversation", {"action": "end_talk"})]

        remaining = []
        if self.tree.current_node == "start":
            remaining = self._filtered_choices()
        else:
            completed = set(self._progress(self.tree_id).get("completed_branches", []))
            for target in self.tree.branch_targets_from_start():
                if target not in completed:
                    remaining.append(target)

        result: List[Tuple[str, object]] = []
        if remaining:
            result.append(("ถามเรื่องอื่น", {"action": "more_topics"}))
        result.append(("จบการสนทนา", {"action": "end_talk"}))
        return result

    def _mark_visited(self, node_id: str) -> None:
        progress = self._progress(self.tree_id)
        visited = list(progress.get("visited_nodes", []))
        if node_id not in visited:
            visited.append(node_id)
        progress["visited_nodes"] = visited
        progress["current_node"] = self.tree.current_node if self.tree else node_id
        self.session.deep_dialogue_progress[self.tree_id] = progress

    def _mark_branch_complete(self, leaf_node: str) -> None:
        if self.tree is None:
            return
        progress = self._progress(self.tree_id)
        completed = list(progress.get("completed_branches", []))
        for _label, target in self.tree.nodes.get("start", {}).get("choices", []):
            if isinstance(target, str) and self._leads_to(leaf_node, target):
                if target not in completed:
                    completed.append(target)
        if leaf_node not in completed and leaf_node != "start":
            completed.append(leaf_node)
        progress["completed_branches"] = completed
        progress["current_node"] = "start"
        self.session.deep_dialogue_progress[self.tree_id] = progress
        if self.tree:
            self.tree.current_node = "start"

    def _leads_to(self, leaf: str, branch_root: str) -> bool:
        if leaf == branch_root:
            return True
        if self.tree is None:
            return False
        node = self.tree.nodes.get(branch_root, {})
        for item in node.get("choices", []):
            if isinstance(item, (list, tuple)) and len(item) >= 2 and str(item[1]) == leaf:
                return True
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                if self._leads_to(leaf, str(item[1])):
                    return True
        return False

    def _progress(self, tree_id: str) -> Dict[str, Any]:
        return self.session.deep_dialogue_progress.setdefault(
            tree_id,
            {"current_node": "start", "visited_nodes": [], "completed_branches": []},
        )

    def _save_progress(self) -> None:
        if self.tree is None:
            return
        progress = self._progress(self.tree_id)
        progress["current_node"] = self.tree.current_node
        self.session.deep_dialogue_progress[self.tree_id] = progress

    def _check_tree_complete(self) -> None:
        if not self.tree_id:
            return
        progress = self._progress(self.tree_id)
        targets = self.tree.branch_targets_from_start() if self.tree else []
        completed = set(progress.get("completed_branches", []))
        if targets and all(t in completed for t in targets):
            if self.tree_id not in self.session.completed_deep_dialogues:
                self.session.completed_deep_dialogues.append(self.tree_id)

    def draw(self, screen: pygame.Surface) -> None:
        if not self.active:
            return
        if self.box is None:
            self.box = ScrollDialogueBox(screen, self._font_body)
            self._sync_display()
        if self.box is not None:
            self.box.render()
        hint = self._font_hint.render("1-3 choose | ESC exit | Scroll wheel", True, (180, 190, 210))
        screen.blit(hint, (screen.get_width() // 2 - hint.get_width() // 2, screen.get_height() - 28))
