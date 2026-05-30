"""Human-feeling NPC conversations with lightweight session memory."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pygame

from core.fonts import get_dialogue_font, get_game_font
from graphics.dialogue_box import DialogueBox as ScrollDialogueBox


Choice = Dict[str, object]
Memory = Dict[str, object]


NPC_KEYS = {
    "Dr. Chen": "dr_chen",
    "Bob": "bob",
    "Maria": "maria",
    "Old Man Jenkins": "old_man_jenkins",
}


def load_casual_dialogue(path: Optional[Path] = None) -> Dict[str, dict]:
    if path is None:
        path = Path(__file__).resolve().parents[1] / "data" / "casual_dialogue.json"
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def time_period(hour: int) -> str:
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def current_weather(day: int, hour: int) -> str:
    return "rain" if (day * 7 + hour) % 11 in (0, 1, 2) else "clear"


def milestone_key(completed_contracts: List[str]) -> Optional[str]:
    completed = set(completed_contracts)
    if "Moon Landing" in completed:
        return "moon_landing"
    if "Orbit" in completed:
        return "orbit"
    if completed.intersection({"Liftoff", "Tower Clear", "Space"}):
        return "first_launch"
    return None


class CasualDialogueManager:
    def __init__(self, memory: Dict[str, Memory], data: Optional[Dict[str, dict]] = None) -> None:
        self.memory = memory
        self.data = data or load_casual_dialogue()

    def npc_key(self, npc_name: str) -> str:
        return NPC_KEYS.get(npc_name, npc_name.lower().replace(" ", "_").replace(".", ""))

    def build_exchange(
        self,
        npc_name: str,
        hour: int,
        day: int,
        completed_contracts: List[str],
        npc_morale: Optional[Dict[str, int]] = None,
        story_flags: Optional[Dict[str, object]] = None,
        completed_deep_dialogues: Optional[List[str]] = None,
    ) -> Dict[str, object]:
        key = self.npc_key(npc_name)
        morale_key = key if key != "old_man_jenkins" else "jenkins"
        morale = int((npc_morale or {}).get(morale_key, 5))
        flags = story_flags or {}
        npc_data = self.data[key]
        memory = self.memory.setdefault(
            key,
            {
                "met": False,
                "talk_count": 0,
                "last_topic": "",
                "seen_milestones": [],
            },
        )
        memory["talk_count"] = int(memory.get("talk_count", 0)) + 1

        period = time_period(hour)
        weather = current_weather(day, hour)
        rng = random.Random(f"{key}:{day}:{hour}:{memory['talk_count']}")
        greeting = rng.choice(npc_data["greetings"][period])
        weather_line = rng.choice(npc_data.get("weather", {}).get(weather, [""]))

        text_parts = [greeting]
        if weather_line:
            text_parts.append(weather_line)

        deep_ack = {
            "Dr. Chen": "dr_chen_resign",
            "Bob": "bob_engine",
            "Maria": "maria_abort",
            "Old Man Jenkins": "jenkins_firefly",
        }
        done = set(completed_deep_dialogues or [])
        tid = deep_ack.get(npc_name)
        if tid and tid in done:
            ack_lines = {
                "dr_chen_resign": "ดร.เฉิน: เราเล่าเรื่อง Orion ไปแล้ว แต่ถ้ามีคำถามใหม่ ฉันยังฟังอยู่",
                "bob_engine": "บ็อบ: คุยยาวพอแล้ว วันนี้มีแค่เสียงเครื่องยนต์",
                "maria_abort": "มาเรีย: ฉันจำทุกครั้งที่สั่งหยุด ไม่ต้องกลัว",
                "jenkins_firefly": "ลุงเจนกินส์: หิ่งห้อยยังบินอยู่ในหัวฉัน แม้จรวดจะอยู่ใต้ผ้าใบ",
            }
            text_parts.append(ack_lines.get(tid, ""))

        if npc_name == "Bob" and flags.get("bob_injured"):
            text_parts.append("บ็อบยังเดินช้า ๆ จากรอยแผลบนหลังคา แต่ยังยืนยันว่าเครื่องยนต์ต้องได้ยินเสียงของเขา")
        elif morale <= 2:
            text_parts.append("เขาดูเหนื่อยมาก คุณอาจต้องดูแลทีมให้มากขึ้น")
        elif morale >= 8:
            text_parts.append("แววตาของเขาบอกว่าวันนี้เขาพร้อมทำสิ่งที่เป็นไปไม่ได้อีกครั้ง")

        if not bool(memory.get("met")):
            text_parts.append(str(npc_data["intro"]))
            memory["met"] = True
            memory["last_topic"] = "intro"
        else:
            milestone = milestone_key(completed_contracts)
            seen_milestones = list(memory.get("seen_milestones", []))
            if milestone and milestone not in seen_milestones:
                text_parts.append(str(npc_data["milestones"].get(milestone, "")))
                seen_milestones.append(milestone)
                memory["seen_milestones"] = seen_milestones
                memory["last_topic"] = milestone
            else:
                topic_id, line = self._pick_topic(key, rng, memory)
                text_parts.append(line)
                memory["last_topic"] = topic_id

        questions = list(npc_data.get("questions", []))
        rng.shuffle(questions)
        choices: List[Choice] = [
            {"label": str(item["question"]), "answer": str(item["answer"])}
            for item in questions[:3]
        ]
        choices.append({"label": "ไว้คุยกันใหม่นะ", "close": True})

        return {
            "speaker": npc_data.get("display_name", npc_name),
            "text": "\n".join(part for part in text_parts if part),
            "choices": choices,
            "portrait_color": tuple(npc_data.get("portrait_color", [200, 200, 200])),
        }

    def _pick_topic(self, key: str, rng: random.Random, memory: Memory) -> Tuple[str, str]:
        topics = self.data[key].get("topics", {})
        topic_ids = list(topics.keys())
        last_topic = str(memory.get("last_topic", ""))
        choices = [topic for topic in topic_ids if topic != last_topic] or topic_ids
        topic_id = rng.choice(choices)
        return topic_id, str(rng.choice(topics[topic_id]))


class CasualDialogueBox:
    def __init__(self, manager: CasualDialogueManager) -> None:
        self.manager = manager
        self.active = False
        self.npc_name = ""
        self.speaker = ""
        self.text = ""
        self.choices: List[Choice] = []
        self.box: Optional[ScrollDialogueBox] = None
        self.portrait_color = (220, 220, 220)
        self.context_hour = 12
        self.context_day = 1
        self.context_completed: List[str] = []
        self.context_morale: Dict[str, int] = {}
        self.context_flags: Dict[str, object] = {}
        self.context_deep_done: List[str] = []
        self.font_name = get_game_font(24, bold=True)
        self.font_body = get_dialogue_font(24)
        self.font_choice = get_dialogue_font(19)
        self.font_hint = get_game_font(14)

    def open(
        self,
        npc_name: str,
        hour: int,
        day: int,
        completed_contracts: List[str],
        npc_morale: Optional[Dict[str, int]] = None,
        story_flags: Optional[Dict[str, object]] = None,
        completed_deep_dialogues: Optional[List[str]] = None,
    ) -> None:
        self.npc_name = npc_name
        self.context_hour = hour
        self.context_day = day
        self.context_completed = list(completed_contracts)
        self.context_morale = dict(npc_morale or {})
        self.context_flags = dict(story_flags or {})
        self.context_deep_done = list(completed_deep_dialogues or [])
        self._load_exchange(hour, day, completed_contracts)
        self.active = True

    def _load_exchange(self, hour: int, day: int, completed_contracts: List[str]) -> None:
        exchange = self.manager.build_exchange(
            npc_name=self.npc_name,
            hour=hour,
            day=day,
            completed_contracts=completed_contracts,
            npc_morale=getattr(self, "context_morale", None),
            story_flags=getattr(self, "context_flags", None),
            completed_deep_dialogues=getattr(self, "context_deep_done", None),
        )
        self.speaker = str(exchange["speaker"])
        self.text = str(exchange["text"])
        self.choices = list(exchange["choices"])
        color = exchange.get("portrait_color", (220, 220, 220))
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            self.portrait_color = tuple(int(c) for c in color[:3])
        self._sync_box()

    def close(self) -> None:
        self.active = False
        if self.box is not None:
            self.box.hide()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.active:
            return False

        if self.box is not None:
            payload = self.box.handle_event(event)
            if payload is not None:
                if isinstance(payload, dict):
                    self._activate_choice(payload)
                return True

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
                return True
            if pygame.K_1 <= event.key <= pygame.K_9:
                index = event.key - pygame.K_1
                if index < len(self.choices):
                    self._activate_choice(self.choices[index])
                    return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, choice in self.choice_rects:
                if rect.collidepoint(event.pos):
                    self._activate_choice(choice)
                    return True
        return False

    def _activate_choice(self, choice: Choice) -> None:
        if bool(choice.get("close")):
            self.close()
            return
        if choice.get("action") == "more":
            self._load_exchange(self.context_hour, self.context_day, self.context_completed)
            return
        answer = str(choice.get("answer", ""))
        self.text = answer
        self.choices = [
            {"label": "เล่าต่ออีกนิด", "action": "more"},
            {"label": "พอแค่นี้ก่อน", "close": True},
        ]
        self._sync_box()

    def draw(self, screen: pygame.Surface) -> None:
        if not self.active:
            return
        if self.box is None:
            self.box = ScrollDialogueBox(screen, self.font_body)
            self._sync_box()
        self.box.render()

    def _sync_box(self) -> None:
        if self.box is None:
            return
        choices = [(str(choice.get("label", "")), choice) for choice in self.choices[:3]]
        self.box.show(self.speaker, self.text, choices)
