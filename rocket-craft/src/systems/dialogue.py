"""Thai dialogue trees and dialogue box renderer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pygame

from config import SCREEN_HEIGHT, SCREEN_WIDTH
from core.fonts import get_dialogue_font

Choice = Tuple[str, Optional[str]]


class DialogueTree:
    def __init__(self) -> None:
        self.nodes: Dict[str, Dict[str, object]] = {}

    def add_node(self, node_id: str, text: str, choices: Optional[List[Choice]] = None) -> None:
        self.nodes[node_id] = {"text": text, "choices": choices or []}

    def get_node(self, node_id: str) -> Optional[Dict[str, object]]:
        return self.nodes.get(node_id)


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> List[str]:
    lines: List[str] = []
    for raw in str(text).split("\n"):
        words = raw.split(" ")
        if len(words) > 1:
            current = ""
            for word in words:
                candidate = word if not current else f"{current} {word}"
                if font.size(candidate)[0] <= max_width:
                    current = candidate
                else:
                    if current:
                        lines.append(current)
                    current = word
            if current:
                lines.append(current)
            continue
        current = ""
        for ch in raw:
            candidate = current + ch
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = ch
        if current:
            lines.append(current)
    return lines


def load_dialogue_json(path: Optional[Path] = None) -> Dict[str, dict]:
    if path is None:
        path = Path(__file__).resolve().parents[1] / "data" / "dialogue.json"
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _next(value: object) -> Optional[str]:
    if value is None or value == "end":
        return None
    return str(value)


def build_npc_dialogues() -> Dict[str, DialogueTree]:
    data = load_dialogue_json()

    def make(ids: List[str], greeting_id: str) -> DialogueTree:
        tree = DialogueTree()
        for node_id in ids:
            node = data.get(node_id, {})
            choices = [(str(c[0]), _next(c[1])) for c in node.get("choices", []) if len(c) >= 2]
            tree.add_node(node_id, str(node.get("text", "")), choices)
        greeting = tree.get_node(greeting_id)
        if greeting:
            tree.add_node("greeting", str(greeting["text"]), list(greeting["choices"]))
        return tree

    return {
        "Dr. Chen": make(["dr_chen_greeting", "dr_chen_project"], "dr_chen_greeting"),
        "Bob": make(["bob_greeting", "bob_advice"], "bob_greeting"),
        "Maria": make(["maria_greeting", "maria_contracts"], "maria_greeting"),
        "Old Man Jenkins": make(["jenkins_greeting", "jenkins_story"], "jenkins_greeting"),
    }


def build_default_dialogues() -> Dict[str, DialogueTree]:
    return build_npc_dialogues()


class DialogueBox:
    def __init__(self, dialogue_data: Optional[Dict[str, dict]] = None) -> None:
        self.data = dialogue_data or load_dialogue_json()
        self.current_node = "intro"
        self.selected_choice = 0
        self.active = False
        self.font_speaker = get_dialogue_font(22, bold=True)
        self.font_body = get_dialogue_font(18)
        self.font_choice = get_dialogue_font(17)
        self.choice_rects: List[Tuple[pygame.Rect, Optional[str]]] = []

    def open(self, node_id: str = "intro") -> None:
        self.current_node = node_id
        self.selected_choice = 0
        self.active = True

    def close(self) -> None:
        self.active = False
        self.choice_rects = []

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.active:
            return False
        node = self.data.get(self.current_node)
        if not node:
            self.close()
            return True
        choices = node.get("choices", [])
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected_choice = max(0, self.selected_choice - 1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_choice = min(max(0, len(choices) - 1), self.selected_choice + 1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self._activate(choices)
            elif event.key == pygame.K_ESCAPE:
                self.close()
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, (rect, _node) in enumerate(self.choice_rects):
                if rect.collidepoint(event.pos):
                    self.selected_choice = index
                    return self._activate(choices)
        return False

    def _activate(self, choices: list) -> bool:
        if not choices:
            self.close()
            return True
        _, next_node = choices[self.selected_choice]
        if next_node in (None, "end"):
            self.close()
            return True
        self.current_node = str(next_node)
        self.selected_choice = 0
        return False

    def draw(self, screen: pygame.Surface) -> None:
        if not self.active:
            return
        node = self.data.get(self.current_node, {})
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
        panel = pygame.Rect(50, SCREEN_HEIGHT - 250, SCREEN_WIDTH - 100, 200)
        pygame.draw.rect(screen, (30, 34, 44), panel, border_radius=8)
        pygame.draw.rect(screen, (120, 132, 160), panel, 2, border_radius=8)
        speaker = self.font_speaker.render(str(node.get("speaker", "")), True, (255, 200, 50))
        screen.blit(speaker, (panel.x + 20, panel.y + 14))
        y = panel.y + 50
        for line in wrap_text(str(node.get("text", "")), self.font_body, panel.width - 40)[:4]:
            screen.blit(self.font_body.render(line, True, (255, 255, 255)), (panel.x + 20, y))
            y += 26
        self.choice_rects = []
        cy = max(panel.y + 118, y + 6)
        for i, (choice_text, next_node) in enumerate(node.get("choices", [])):
            rect = pygame.Rect(panel.x + 16, cy, panel.width - 32, 28)
            pygame.draw.rect(screen, (48, 56, 76) if i == self.selected_choice else (36, 42, 58), rect, border_radius=4)
            color = (255, 255, 100) if i == self.selected_choice else (220, 220, 230)
            label = self.font_choice.render(f"{i + 1}. {choice_text}", True, color)
            screen.blit(label, (rect.x + 10, rect.y + 5))
            self.choice_rects.append((rect, _next(next_node)))
            cy += 34
