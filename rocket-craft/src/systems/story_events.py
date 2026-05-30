"""Story-driven daily events — choice consequences, morale, and flags."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pygame

from config import SCREEN_HEIGHT, SCREEN_WIDTH
from core.fonts import get_dialogue_font, get_game_font
from core.game_session import GameSession
from systems.dialogue import wrap_text

NPC_LABELS: Dict[str, str] = {
    "bob": "Bob",
    "dr_chen": "Dr. Chen",
    "maria": "Maria",
    "jenkins": "Old Man Jenkins",
    "old_man_jenkins": "Old Man Jenkins",
}


class StoryEventManager:
    """Loads scripted events and applies player choices to session state."""

    def __init__(self, session: GameSession, data_path: Optional[Path] = None) -> None:
        self.session = session
        if data_path is None:
            data_path = Path(__file__).resolve().parents[1] / "data" / "story_events.json"
        self.data_path = data_path
        self.events: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        try:
            with open(self.data_path, "r", encoding="utf-8") as handle:
                self.events = json.load(handle)
        except (OSError, json.JSONDecodeError):
            self.events = {}

    def pending_for(self, day: int, trigger: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Return the first eligible event id and payload for this day/trigger."""
        def sort_key(item: Tuple[str, Dict[str, Any]]) -> Tuple[int, str]:
            return int(item[1].get("day", 0)), item[0]

        for event_id, event in sorted(self.events.items(), key=sort_key):
            if event_id in self.session.story_completed_events:
                continue
            if int(event.get("day", -1)) != day:
                continue
            triggers = event.get("trigger", [])
            if isinstance(triggers, str):
                triggers = [triggers]
            if trigger not in triggers and "any" not in triggers:
                continue
            if not self._requirements_met(event.get("requires", {})):
                continue
            return event_id, event
        return None

    def check_events(self, day: int, player_location: str) -> Optional[Dict[str, Any]]:
        """Compatibility helper that returns an event payload with its id."""
        pending = self.pending_for(day, player_location)
        if pending is None:
            return None
        event_id, event = pending
        payload = dict(event)
        payload["id"] = event_id
        return payload

    def _requirements_met(self, requires: Any) -> bool:
        if not isinstance(requires, dict) or not requires:
            return True
        flags = self.session.story_flags
        for key, expected in requires.items():
            if key == "completed_event":
                values = expected if isinstance(expected, list) else [expected]
                if not all(str(value) in self.session.story_completed_events for value in values):
                    return False
                continue
            if key == "not_completed_event":
                values = expected if isinstance(expected, list) else [expected]
                if any(str(value) in self.session.story_completed_events for value in values):
                    return False
                continue
            if flags.get(key) != expected:
                return False
        return True

    def choice_affordable(self, choice: Dict[str, Any]) -> bool:
        money_delta = self._money_delta(choice)
        if money_delta >= 0:
            return True
        return self.session.money + money_delta >= 0

    def apply_choice(self, event_id: str, choice_index: int) -> str:
        event = self.events.get(event_id, {})
        choices = event.get("choices", [])
        if not (0 <= choice_index < len(choices)):
            return ""
        choice = choices[choice_index]
        if not self.choice_affordable(choice):
            return "Not enough funds for that choice."

        self.session.money += self._money_delta(choice)
        self.session.reputation += int(choice.get("reputation_delta", 0))
        self.session.research_points += int(choice.get("research_delta", 0))

        for npc_key, delta in dict(choice.get("morale_delta", {})).items():
            self._adjust_morale(npc_key, int(delta))

        for flag_key, value in dict(choice.get("flags", {})).items():
            self.session.story_flags[flag_key] = value

        contract = choice.get("complete_contract")
        if contract and contract not in self.session.completed_contracts:
            self.session.completed_contracts.append(str(contract))

        self._apply_unlocks(choice.get("unlock_parts", []))
        self._apply_legacy_result(choice.get("result", {}))

        mail_items = choice.get("add_mail", [])
        if isinstance(mail_items, dict):
            mail_items = [mail_items]
        for mail in mail_items:
            if isinstance(mail, dict):
                self._add_mail(mail)

        self._apply_special_rules(event_id, choice)

        self.session.story_choices[event_id] = choice_index
        if event_id not in self.session.story_completed_events:
            self.session.story_completed_events.append(event_id)

        return str(choice.get("result_text", "The team moves on."))

    def _money_delta(self, choice: Dict[str, Any]) -> int:
        if "money_delta" in choice:
            return int(choice.get("money_delta", 0))
        if "cost" in choice:
            return -int(choice.get("cost", 0))
        return 0

    def _adjust_morale(self, npc_key: str, delta: int) -> None:
        key = str(npc_key).strip().lower().replace(" ", "_")
        if key in ("dr.chen", "dr._chen"):
            key = "dr_chen"
        if key in ("old_man_jenkins", "old_jenkins"):
            key = "jenkins"
        current = int(self.session.npc_morale.get(key, 5))
        self.session.npc_morale[key] = max(0, min(10, current + delta))

    def _add_mail(self, mail: Dict[str, Any]) -> None:
        mail_id = str(mail.get("id", ""))
        if not mail_id:
            return
        existing = {str(item.get("id", "")) for item in self.session.mailbox}
        if mail_id in existing:
            return
        self.session.mailbox.append(
            {
                "id": mail_id,
                "from": mail.get("from", "Unknown"),
                "subject": mail.get("subject", ""),
                "body": mail.get("body", ""),
                "day": self.session.time.day,
                "read": False,
            }
        )

    def _apply_unlocks(self, unlock_parts: Any) -> None:
        if isinstance(unlock_parts, str):
            parts = [unlock_parts]
        elif isinstance(unlock_parts, list):
            parts = [str(part) for part in unlock_parts]
        else:
            parts = []
        for part_key in parts:
            if part_key not in self.session.unlocked_parts:
                self.session.unlocked_parts.append(part_key)

    def _apply_legacy_result(self, result: Any) -> None:
        if not isinstance(result, dict):
            return
        for key, value in result.items():
            clean_key = str(key)
            if clean_key.endswith("_morale"):
                self._adjust_morale(clean_key[: -len("_morale")], int(value))
            else:
                self.session.story_flags[clean_key] = value

    def _apply_special_rules(self, event_id: str, choice: Dict[str, Any]) -> None:
        if event_id == "day_9_hangar_leak" and choice.get("text", "").startswith("Let Bob"):
            if random.random() < 0.2:
                self._adjust_morale("bob", -2)
                self.session.story_flags["bob_injured"] = True
                self.session.story_flags["bob_injured_days"] = 3
        if event_id == "day_8_orion_warning" and "fuel formula" in str(choice.get("text", "")).lower():
            if "safely" in str(choice.get("text", "")).lower():
                self.session.time.day += 2
                self.session.time.hour = 6
                self.session.time.minute = 0.0

    def morale_label(self, npc_key: str) -> str:
        value = int(self.session.npc_morale.get(npc_key, 5))
        if value >= 8:
            return "Inspired"
        if value >= 6:
            return "Steady"
        if value >= 4:
            return "Tired"
        return "Low"


class StoryEventUI:
    """Modal story event panel with Thai NPC lines and English UI chrome."""

    def __init__(self, manager: StoryEventManager) -> None:
        self.manager = manager
        self.active = False
        self.event_id = ""
        self.event_data: Dict[str, Any] = {}
        self.selected_choice = 0
        self.result_text = ""
        self.showing_result = False
        self.font_title = get_game_font(22, bold=True)
        self.font_body = get_dialogue_font(17)
        self.font_npc = get_dialogue_font(16)
        self.font_choice = get_dialogue_font(16)
        self.font_small = get_game_font(14)
        self.choice_rects: List[pygame.Rect] = []

    def try_open(self, trigger: str) -> bool:
        if self.active:
            return True
        pending = self.manager.pending_for(self.manager.session.time.day, trigger)
        if pending is None:
            return False
        event_id, event_data = pending
        self.open(event_id, event_data)
        return True

    def open(self, event_id: str, event_data: Dict[str, Any]) -> None:
        self.active = True
        self.event_id = event_id
        self.event_data = event_data
        self.selected_choice = 0
        self.result_text = ""
        self.showing_result = False
        self.choice_rects = []

    def close(self) -> None:
        self.active = False
        self.event_id = ""
        self.event_data = {}
        self.showing_result = False
        self.choice_rects = []

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.active:
            return False

        if self.showing_result:
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_RETURN,
                pygame.K_SPACE,
                pygame.K_ESCAPE,
            ):
                self.close()
                return True
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.close()
                return True
            return True

        choices = self.event_data.get("choices", [])
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected_choice = max(0, self.selected_choice - 1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_choice = min(max(0, len(choices) - 1), self.selected_choice + 1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate_choice()
            elif event.key == pygame.K_ESCAPE:
                self.close()
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, rect in enumerate(self.choice_rects):
                if rect.collidepoint(event.pos):
                    self.selected_choice = index
                    self._activate_choice()
                    return True
        return True

    def _activate_choice(self) -> None:
        choices = self.event_data.get("choices", [])
        if not choices:
            self.close()
            return
        choice = choices[self.selected_choice]
        if not self.manager.choice_affordable(choice):
            self.result_text = "Not enough funds for that choice."
            self.showing_result = True
            return
        self.result_text = self.manager.apply_choice(self.event_id, self.selected_choice)
        self.showing_result = True

    def draw(self, screen: pygame.Surface) -> None:
        if not self.active:
            return

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        panel = pygame.Rect(44, SCREEN_HEIGHT - 320, SCREEN_WIDTH - 88, 280)
        pygame.draw.rect(screen, (26, 30, 42), panel, border_radius=10)
        pygame.draw.rect(screen, (120, 132, 160), panel, 2, border_radius=10)

        day = int(self.event_data.get("day", self.manager.session.time.day))
        title = self.font_title.render(
            f"Day {day} — {self.event_data.get('title', 'Story Event')}",
            True,
            (255, 236, 39),
        )
        screen.blit(title, (panel.x + 18, panel.y + 12))

        y = panel.y + 46
        if not self.showing_result:
            for line in wrap_text(str(self.event_data.get("description", "")), self.font_body, panel.width - 36)[:3]:
                screen.blit(self.font_body.render(line, True, (235, 238, 245)), (panel.x + 18, y))
                y += 24

            npc_lines = dict(self.event_data.get("npc_dialogues", {}))
            for npc_key, thai_text in npc_lines.items():
                label = NPC_LABELS.get(npc_key, npc_key.replace("_", " ").title())
                line = f"{label}: {thai_text}"
                for wrapped in wrap_text(line, self.font_npc, panel.width - 36)[:2]:
                    screen.blit(self.font_npc.render(wrapped, True, (200, 220, 255)), (panel.x + 18, y))
                    y += 22

            self.choice_rects = []
            choices = self.event_data.get("choices", [])
            cy = max(panel.y + 150, y + 8)
            for index, choice in enumerate(choices):
                rect = pygame.Rect(panel.x + 14, cy, panel.width - 28, 30)
                affordable = self.manager.choice_affordable(choice)
                base_color = (48, 56, 76) if index == self.selected_choice else (36, 42, 58)
                if not affordable:
                    base_color = (56, 40, 40)
                pygame.draw.rect(screen, base_color, rect, border_radius=4)
                color = (255, 255, 120) if index == self.selected_choice else (220, 224, 235)
                if not affordable:
                    color = (200, 140, 140)
                label = self.font_choice.render(f"{index + 1}. {choice.get('text', '')}", True, color)
                screen.blit(label, (rect.x + 8, rect.y + 6))
                self.choice_rects.append(rect)
                cy += 36
        else:
            for line in wrap_text(self.result_text, self.font_body, panel.width - 36):
                screen.blit(self.font_body.render(line, True, (255, 255, 255)), (panel.x + 18, y))
                y += 24
            hint = self.font_small.render("Press Enter to continue", True, (180, 190, 210))
            screen.blit(hint, (panel.x + 18, panel.bottom - 34))
