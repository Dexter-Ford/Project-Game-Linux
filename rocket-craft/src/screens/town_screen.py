"""Town overview: buildings, walkable NPCs, Thai dialogue, day/night."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pygame

from config import SCREEN_HEIGHT, SCREEN_WIDTH
from core.fonts import get_dialogue_font, get_game_font
from core.game_session import GameSession
from entities.npc import NPC
from graphics.building_renderer import BuildingRenderer
from graphics.sky import SkyRenderer
from graphics.town_roads import TownRoadRenderer
from graphics.vegetation import VegetationManager
from systems.casual_dialogue import CasualDialogueBox, CasualDialogueManager
from systems.deep_dialogue import DeepDialogueController
from systems.dialogue import DialogueBox, wrap_text
from systems.story_events import StoryEventManager, StoryEventUI
from systems.town_map import TownMap
from systems.town_zones import ZONES, get_zone_at

try:
    from audio.audio_manager import AudioManager
except ImportError:
    AudioManager = None  # type: ignore[misc, assignment]


Color = Tuple[int, int, int]

NPC_MORALE_KEYS = {
    "Dr. Chen": "dr_chen",
    "Bob": "bob",
    "Maria": "maria",
    "Old Man Jenkins": "jenkins",
}

NPC_HOME_RENDER_TYPES = {
    "Bob": "home_bob",
    "Dr. Chen": "home_chen",
    "Maria": "home_maria",
    "Old Man Jenkins": "home_jenkins",
}

HOME_LABEL_COLORS = {
    "house": (255, 236, 120),
    "home_bob": (255, 190, 110),
    "home_chen": (150, 200, 255),
    "home_maria": (255, 180, 200),
    "home_jenkins": (190, 220, 160),
}


class TownCamera:
    def __init__(self, bounds: Tuple[int, int]) -> None:
        self.bounds = bounds
        self.x = 0.0
        self.y = 0.0
        self.pan_speed = 420.0
        self.clamp()

    def update(self, dt: float) -> None:
        mouse_x, mouse_y = pygame.mouse.get_pos()
        margin = 28
        if mouse_x < margin:
            self.x -= self.pan_speed * dt
        elif mouse_x > SCREEN_WIDTH - margin:
            self.x += self.pan_speed * dt
        if mouse_y < margin:
            self.y -= self.pan_speed * dt
        elif mouse_y > SCREEN_HEIGHT - margin:
            self.y += self.pan_speed * dt
        self.clamp()

    def clamp(self) -> None:
        world_w, world_h = self.bounds
        if world_w <= SCREEN_WIDTH:
            self.x = -(SCREEN_WIDTH - world_w) / 2
        else:
            self.x = max(0.0, min(self.x, world_w - SCREEN_WIDTH))
        if world_h <= SCREEN_HEIGHT:
            self.y = -(SCREEN_HEIGHT - world_h) / 2
        else:
            self.y = max(0.0, min(self.y, world_h - SCREEN_HEIGHT))

    def world_to_screen(self, world_x: float, world_y: float) -> Tuple[int, int]:
        return int(world_x - self.x), int(world_y - self.y)

    def screen_to_world(self, screen_x: int, screen_y: int) -> Tuple[float, float]:
        return screen_x + self.x, screen_y + self.y


@dataclass
class Building:
    name: str
    rect: pygame.Rect
    color: Color
    action: str


class TownScreen:
    def __init__(self, session: GameSession, audio: "AudioManager | None" = None) -> None:
        self.session = session
        self.audio = audio
        self.bounds = (1680, 1040)
        self.camera = TownCamera(self.bounds)
        self.font = get_game_font(16)
        self.font_small = get_game_font(13)
        self.font_title = get_game_font(22, bold=True)
        self.font_dialogue = get_dialogue_font(17)
        self.font_dialogue_small = get_dialogue_font(15)
        self.sky = SkyRenderer(seed=101)
        self.building_renderer = BuildingRenderer()
        self.road_renderer = TownRoadRenderer()

        self.buildings = self._make_buildings()
        self.path_routes = self._make_road_network()
        self.town_map = TownMap(
            self.bounds[0],
            self.bounds[1],
            blocked_rects=[b.rect for b in self.buildings],
        )
        self.vegetation = VegetationManager(
            self.town_map,
            self.bounds,
            [b.rect for b in self.buildings],
            seed=42,
            path_points=[pt for route in self.path_routes for pt in route],
        )

        self.player_x = 820.0
        self.player_y = 700.0
        self.player_target_x = self.player_x
        self.player_target_y = self.player_y
        self.current_zone = get_zone_at(self.player_x, self.player_y)
        self.camera.x = self.player_x - SCREEN_WIDTH / 2
        self.camera.y = self.player_y - SCREEN_HEIGHT / 2
        self.camera.clamp()
        self.zone_targets = {
            "hangar_area": (455.0, 750.0),
            "research_zone": (1320.0, 520.0),
            "supply_zone": (1260.0, 900.0),
            "mission_zone": (760.0, 520.0),
            "plaza": (820.0, 700.0),
        }
        self.npc_schedule_targets = {
            "Dr. Chen": {"work": (1315.0, 525.0), "home": (1408.0, 520.0), "evening": (890.0, 725.0)},
            "Bob": {"work": (345.0, 750.0), "home": (1098.0, 940.0), "evening": (785.0, 745.0)},
            "Maria": {"work": (735.0, 515.0), "home": (958.0, 405.0), "evening": (840.0, 735.0)},
            "Old Man Jenkins": {"work": (900.0, 750.0), "home": (358.0, 920.0), "evening": (900.0, 750.0)},
        }
        self._npc_schedule_hour: Optional[int] = None
        self._npc_schedule_timer = 0.0

        self.npcs = [
            NPC("Dr. Chen", "Scientist", 1315, 525, (110, 210, 255), seed=1),
            NPC("Bob", "Engineer", 330, 890, (255, 170, 70), seed=2),
            NPC("Maria", "Mission Control", 735, 515, (255, 110, 150), seed=3),
            NPC("Old Man Jenkins", "Old Man Jenkins", 835, 825, (180, 170, 140), seed=4),
        ]
        self._restore_npc_positions()
        for npc in self.npcs:
            npc.pick_random_target(self.town_map)

        self.dialogue_manager = CasualDialogueManager(self.session.npc_memory)
        self.casual_dialogue = CasualDialogueBox(self.dialogue_manager)
        self.deep_dialogue = DeepDialogueController(session)
        self.intro_dialogue = DialogueBox()
        self.story_manager = StoryEventManager(session)
        self.story_ui = StoryEventUI(self.story_manager)
        self.active_npc: Optional[NPC] = None
        self.notice = ""
        self.notice_timer = 0.0
        self._town_entered = False
        self._last_day = session.time.day
        self.deferred_action: Optional[str] = None
        self.map_open = False
        self.mailbox_open = False
        self.mail_scroll = 0
        self.mailbox_rect = pygame.Rect(530, 780, 34, 46)
        self._ensure_mail()

        self.quick_buttons = [
            (pygame.Rect(22, SCREEN_HEIGHT - 62, 122, 40), "Hangar", "hangar"),
            (pygame.Rect(154, SCREEN_HEIGHT - 62, 136, 40), "Research", "research"),
            (pygame.Rect(300, SCREEN_HEIGHT - 62, 118, 40), "Supply", "shop"),
            (pygame.Rect(428, SCREEN_HEIGHT - 62, 144, 40), "Contracts", "contracts"),
            (pygame.Rect(582, SCREEN_HEIGHT - 62, 98, 40), "Map", "map"),
        ]

    def on_enter(self) -> None:
        if not self.session.seen_town_intro:
            self.intro_dialogue.open("intro")
            self.session.seen_town_intro = True
        self._town_entered = True
        self._ensure_mail()
        if not self.session.story_flags.get("seen_homes_hint"):
            self.notice = "Follow the paved roads — homes are spread across the valley."
            self.notice_timer = 5.5
            self.session.story_flags["seen_homes_hint"] = True

    def _ensure_mail(self) -> None:
        existing_ids = {str(mail.get("id", "")) for mail in self.session.mailbox}
        starter_mail = [
            {
                "id": "welcome_council",
                "from": "Town Council",
                "subject": "Welcome to your cottage",
                "body": "Welcome home. The cottage is yours to arrange. Check the decor desk inside when you want to change the room.",
            },
            {
                "id": "bob_tools",
                "from": "Bob",
                "subject": "Mailbox works",
                "body": "I fixed the mailbox hinge. It squeaks less now. That is progress.",
            },
        ]
        for mail in starter_mail:
            if mail["id"] not in existing_ids:
                self.session.mailbox.append({**mail, "day": self.session.time.day, "read": False})
                existing_ids.add(mail["id"])

        milestone_mail = [
            (
                "Liftoff",
                {
                    "id": "liftoff_maria",
                    "from": "Maria",
                    "subject": "Launch log attached",
                    "body": "That first liftoff was louder than the numbers suggested. I saved the cleanest telemetry page for you.",
                },
            ),
            (
                "Orbit",
                {
                    "id": "orbit_chen",
                    "from": "Dr. Chen",
                    "subject": "About that orbit",
                    "body": "I keep replaying the orbit plot. It looks like proof, but it also looks like a promise.",
                },
            ),
        ]
        completed = set(self.session.completed_contracts)
        for milestone, mail in milestone_mail:
            if milestone in completed and mail["id"] not in existing_ids:
                self.session.mailbox.append({**mail, "day": self.session.time.day, "read": False})
                existing_ids.add(mail["id"])

    def _unread_mail_count(self) -> int:
        return sum(1 for mail in self.session.mailbox if not bool(mail.get("read", False)))

    def _restore_npc_positions(self) -> None:
        expected_zones = {
            "Dr. Chen": "research_zone",
            "Bob": "hangar_area",
            "Maria": "mission_zone",
            "Old Man Jenkins": "plaza",
        }
        for npc in self.npcs:
            pos = self.session.npc_positions.get(npc.name)
            if pos and len(pos) >= 2:
                x, y = float(pos[0]), float(pos[1])
                zone_id = expected_zones.get(npc.name)
                in_expected_zone = True
                if zone_id is not None:
                    bx, by, bw, bh = ZONES[zone_id]["bounds"]
                    in_expected_zone = bx <= x <= bx + bw and by <= y <= by + bh
                if self.town_map.is_walkable(x, y) and in_expected_zone:
                    npc.x, npc.y = x, y
                    npc.target_x, npc.target_y = x, y

    def _save_npc_positions(self) -> None:
        for npc in self.npcs:
            self.session.npc_positions[npc.name] = [npc.x, npc.y]

    def _time_frozen(self) -> bool:
        return (
            self.intro_dialogue.active
            or self.casual_dialogue.active
            or self.map_open
            or self.mailbox_open
            or self.story_ui.active
            or self.deep_dialogue.active
        )

    def consume_deferred_action(self) -> Optional[str]:
        if self.story_ui.active:
            return None
        action = self.deferred_action
        self.deferred_action = None
        return action

    def update(self, dt: float) -> None:
        frozen = self._time_frozen()
        if not frozen:
            self.camera.update(dt)

        self.session.time.paused = frozen
        day_rolled = self.session.time.update(dt)
        if day_rolled:
            self._on_new_day()
        light = self.session.time.get_light_level()
        self.sky.update(dt, light)
        self.road_renderer.update(dt)

        if self.notice_timer > 0:
            self.notice_timer -= dt
        self._ensure_mail()

        if not frozen:
            self._update_npc_schedules(dt)
            for npc in self.npcs:
                npc.update(dt, self.town_map)
            self._update_player(dt)
        self._save_npc_positions()

        zone = get_zone_at(self.player_x, self.player_y)
        if zone != self.current_zone:
            prev_zone = self.current_zone
            self.current_zone = zone
            if self.audio is not None:
                path = self.audio.zone_music_path(zone)
                if path is not None:
                    self.audio.play_music(path, fade_ms=800)
            self._on_zone_enter(zone, prev_zone)

    def _on_new_day(self) -> None:
        self._last_day = self.session.time.day
        injured_days = int(self.session.story_flags.get("bob_injured_days", 0))
        if injured_days > 0:
            self.session.story_flags["bob_injured_days"] = injured_days - 1
            if injured_days - 1 <= 0:
                self.session.story_flags.pop("bob_injured", None)

    def _update_npc_schedules(self, dt: float) -> None:
        hour = self.session.time.hour
        self._npc_schedule_timer -= dt
        if self._npc_schedule_hour == hour and self._npc_schedule_timer > 0:
            return

        self._npc_schedule_hour = hour
        self._npc_schedule_timer = 7.0
        for npc in self.npcs:
            targets = self.npc_schedule_targets.get(npc.name)
            if not targets:
                continue
            period = self._npc_schedule_period(npc.name)
            tx, ty = targets.get(period, targets["work"])
            tx, ty = self.town_map.clamp_to_walkable(tx, ty)
            dx = npc.x - tx
            dy = npc.y - ty
            if dx * dx + dy * dy > 24.0 * 24.0:
                npc.target_x = tx
                npc.target_y = ty
                npc.wait_time = min(npc.wait_time, 0.4)
            else:
                npc.target_x = tx
                npc.target_y = ty
                npc.wait_time = max(npc.wait_time, 3.0)

    def _npc_schedule_period(self, npc_name: str) -> str:
        hour = self.session.time.hour
        morale_key = NPC_MORALE_KEYS.get(npc_name, "")
        morale = int(self.session.npc_morale.get(morale_key, 5))
        if npc_name == "Bob" and self.session.story_flags.get("bob_injured"):
            return "home"
        if morale <= 1 and 8 <= hour < 18:
            return "home"
        if 8 <= hour < 18:
            return "work"
        if 18 <= hour < 22:
            return "evening"
        return "home"

    def _on_zone_enter(self, zone: str, _prev_zone: str) -> None:
        zone_triggers = {
            "plaza": "plaza",
            "hangar_area": "hangar_area",
            "mission_zone": "mission_zone",
        }
        trigger = zone_triggers.get(zone)
        if trigger:
            self._try_story(trigger)

    def _try_story(self, trigger: str, defer_screen: Optional[str] = None) -> bool:
        if self.story_ui.try_open(trigger):
            if defer_screen:
                self.deferred_action = defer_screen
            if self.audio:
                self.audio.play_sfx("click")
            return True
        return False

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if self.story_ui.active:
            was_active = self.story_ui.active
            self.story_ui.handle_event(event)
            if was_active and not self.story_ui.active and self.audio:
                self.audio.play_sfx("confirm")
            return None

        if self.deep_dialogue.active:
            self.deep_dialogue.handle_event(event)
            if not self.deep_dialogue.active:
                self.active_npc = None
                if self.audio:
                    self.audio.play_sfx("confirm")
            return None

        if self.intro_dialogue.active:
            if self.intro_dialogue.handle_event(event):
                return None
            return None

        if self.casual_dialogue.active:
            self.casual_dialogue.handle_event(event)
            if not self.casual_dialogue.active:
                self.active_npc = None
            return None

        if self.mailbox_open:
            self._handle_mailbox_event(event)
            return None

        if self.map_open:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_m):
                self.map_open = False
                return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_map_click(event.pos)
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "title"
            if event.key == pygame.K_m:
                self.map_open = True
                return None
            if event.key == pygame.K_e:
                if self._near_mailbox():
                    self._open_mailbox()
                    return None
                npc = self._nearest_npc()
                if npc is not None:
                    self._open_npc_dialogue(npc)
                return None

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return None

        mouse_pos = pygame.mouse.get_pos()
        for rect, _label, action in self.quick_buttons:
            if rect.collidepoint(mouse_pos):
                return self._trigger_action(action)

        world_x, world_y = self.camera.screen_to_world(*mouse_pos)
        if self.mailbox_rect.collidepoint(world_x, world_y):
            self._open_mailbox()
            return None

        for npc in self.npcs:
            if npc.contains_point(world_x, world_y):
                self._open_npc_dialogue(npc)
                return None

        for building in self.buildings:
            if building.rect.collidepoint(world_x, world_y):
                return self._trigger_action(building.action)

        if self.town_map.is_walkable(world_x, world_y):
            self.player_target_x = world_x
            self.player_target_y = world_y
        return None

    def _nearest_npc(self) -> Optional[NPC]:
        best: Optional[NPC] = None
        best_dist = 64.0 * 64.0
        for npc in self.npcs:
            dx = npc.x - self.player_x
            dy = npc.y - self.player_y
            dist = dx * dx + dy * dy
            if dist < best_dist:
                best_dist = dist
                best = npc
        return best

    def _open_npc_dialogue(self, npc: NPC) -> None:
        if npc.name == "Bob" and self.session.story_flags.get("bob_injured"):
            self.notice = "Bob is recovering from the roof fall (cannot work today)."
            self.notice_timer = 3.0
            return
        self.active_npc = npc
        if self.audio:
            self.audio.play_sfx("click")

        if self.deep_dialogue.should_use_deep(npc.name):
            self.deep_dialogue.open(npc.name)
            return

        self.casual_dialogue.open(
            npc.name,
            self.session.time.hour,
            self.session.time.day,
            self.session.completed_contracts,
            npc_morale=self.session.npc_morale,
            story_flags=self.session.story_flags,
            completed_deep_dialogues=self.session.completed_deep_dialogues,
        )

    def _near_building(self, building: Building) -> bool:
        cx = building.rect.centerx
        cy = building.rect.centery
        dx = self.player_x - cx
        dy = self.player_y - cy
        radius = max(building.rect.width, building.rect.height) * 0.75 + 24
        return dx * dx + dy * dy <= radius * radius

    def _near_mailbox(self) -> bool:
        dx = self.player_x - self.mailbox_rect.centerx
        dy = self.player_y - self.mailbox_rect.centery
        return dx * dx + dy * dy <= 58.0 * 58.0

    def _open_mailbox(self) -> None:
        if self._try_story("mailbox"):
            return
        self.mailbox_open = True
        self.mail_scroll = 0
        for mail in self.session.mailbox:
            mail["read"] = True
        if self.audio:
            self.audio.play_sfx("click")

    def _handle_mailbox_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.mailbox_open = False
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:
                self.mail_scroll = max(0, self.mail_scroll - 1)
            elif event.button == 5:
                self.mail_scroll = min(max(0, len(self.session.mailbox) - 3), self.mail_scroll + 1)
            elif event.button == 1:
                panel = pygame.Rect(0, 0, 720, 500)
                panel.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                close_rect = pygame.Rect(panel.right - 96, panel.y + 18, 72, 32)
                if close_rect.collidepoint(event.pos):
                    self.mailbox_open = False

    def draw(self, screen: pygame.Surface) -> None:
        light = self.session.time.get_light_level()
        is_night = light < 0.45

        self.sky.draw(screen, light)
        self._draw_ground(screen, light)
        self._draw_zone_backgrounds(screen, light)
        self._draw_scenic_details(screen, light)
        if self.vegetation is not None:
            self.vegetation.draw(screen, self.camera, light)
        self._draw_paths(screen, light)
        self._draw_buildings(screen, is_night)
        self._draw_mailbox(screen)
        for npc in self.npcs:
            npc.render(screen, self.camera, self.font_small)
        self._draw_player(screen)
        self._draw_hud(screen, light)

        if self.story_ui.active:
            self.story_ui.draw(screen)
        elif self.deep_dialogue.active:
            self.deep_dialogue.draw(screen)
        elif self.intro_dialogue.active:
            self.intro_dialogue.draw(screen)
        elif self.casual_dialogue.active:
            self.casual_dialogue.draw(screen)
        elif self.map_open:
            self._draw_full_map(screen)
        elif self.mailbox_open:
            self._draw_mailbox_overlay(screen)
        elif self.notice_timer > 0:
            self._draw_notice(screen, self.notice)

    def _make_road_network(self) -> List[List[Tuple[float, float]]]:
        """Paved routes linking plaza, facilities, and homes across the valley."""
        plaza = (820.0, 700.0)
        return [
            [(200.0, 720.0), (455.0, 715.0), (650.0, 705.0), plaza, (1030.0, 705.0), (1280.0, 720.0), (1520.0, 735.0)],
            [plaza, (820.0, 560.0), (820.0, 430.0), (950.0, 400.0)],
            [plaza, (820.0, 820.0), (680.0, 900.0), (420.0, 920.0), (280.0, 915.0)],
            [plaza, (980.0, 820.0), (1080.0, 880.0), (1180.0, 920.0)],
            [(455.0, 715.0), (380.0, 680.0), (300.0, 600.0), (260.0, 540.0)],
            [(1030.0, 705.0), (1180.0, 620.0), (1320.0, 540.0), (1400.0, 500.0)],
            [(1280.0, 870.0), (1260.0, 820.0), (1255.0, 760.0)],
            [(820.0, 560.0), (700.0, 500.0), (620.0, 455.0)],
        ]

    def _make_buildings(self) -> List[Building]:
        house_label = f"{self.session.player_name}'s House"
        return [
            Building("Rocket Hangar", pygame.Rect(130, 675, 250, 148), (92, 96, 104), "hangar"),
            Building(house_label, pygame.Rect(200, 470, 120, 80), (220, 210, 195), "house"),
            Building("Bob's Place", pygame.Rect(1040, 900, 115, 78), (214, 190, 164), "npc_home:Bob"),
            Building("Jenkins Cabin", pygame.Rect(300, 880, 115, 78), (196, 180, 150), "npc_home:Old Man Jenkins"),
            Building("Research Lab", pygame.Rect(1240, 360, 150, 110), (218, 226, 232), "research"),
            Building("Dr. Chen's Cottage", pygame.Rect(1350, 480, 115, 78), (206, 224, 232), "npc_home:Dr. Chen"),
            Building("Supply Depot", pygame.Rect(1200, 780, 120, 84), (150, 92, 56), "shop"),
            Building("Mission Control", pygame.Rect(560, 350, 160, 116), (66, 128, 196), "contracts"),
            Building("Maria's Flat", pygame.Rect(900, 360, 115, 78), (220, 210, 218), "npc_home:Maria"),
        ]

    def _building_render_type(self, building: Building) -> str:
        if building.action.startswith("npc_home:"):
            owner = building.action.split(":", 1)[1]
            return NPC_HOME_RENDER_TYPES.get(owner, "house")
        return building.action

    def refresh_building_labels(self) -> None:
        """Update dynamic labels (e.g. player house name) after load."""
        self.buildings = self._make_buildings()
        blocked = [b.rect for b in self.buildings]
        self.town_map = TownMap(self.bounds[0], self.bounds[1], blocked_rects=blocked)
        self.path_routes = self._make_road_network()
        path_points = [pt for route in self.path_routes for pt in route]
        self.vegetation = VegetationManager(
            self.town_map,
            self.bounds,
            blocked,
            seed=42,
            path_points=path_points,
        )
        self.building_renderer.clear_cache()

    def _trigger_action(self, action: str) -> Optional[str]:
        story_triggers = {
            "hangar": ("hangar", "hangar"),
            "house": (None, None),
            "contracts": ("contracts", None),
        }
        if action in story_triggers:
            trigger, defer = story_triggers[action]
            if trigger and self._try_story(trigger, defer_screen=defer):
                return None

        if self.audio:
            self.audio.play_sfx("click")
        if action == "hangar":
            return "hangar"
        if action == "house":
            return "house"
        if action.startswith("npc_home:"):
            return action
        if action == "map":
            self.map_open = True
            return None
        if action == "research":
            self._set_target_to_zone("research_zone")
            self.notice = "Research Ridge marked."
        elif action == "contracts":
            if self._try_story("mission_zone"):
                return None
            self._set_target_to_zone("mission_zone")
            self.notice = "Mission Control marked."
        elif action == "shop":
            self._set_target_to_zone("supply_zone")
            self.notice = "Supply Yard marked."
        self.notice_timer = 2.8
        return None

    def _set_target_to_zone(self, zone_id: str) -> None:
        if zone_id in self.zone_targets:
            cx, cy = self.zone_targets[zone_id]
        else:
            bx, by, bw, bh = ZONES[zone_id]["bounds"]
            cx, cy = bx + bw / 2, by + bh / 2
        self.player_target_x, self.player_target_y = self.town_map.clamp_to_walkable(cx, cy)

    def _update_player(self, dt: float) -> None:
        dx = self.player_target_x - self.player_x
        dy = self.player_target_y - self.player_y
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 2.0:
            return
        speed = 120.0
        step = min(dist, speed * dt)
        nx = self.player_x + (dx / dist) * step
        ny = self.player_y + (dy / dist) * step
        if self.town_map.is_walkable(nx, ny):
            self.player_x, self.player_y = nx, ny

    def _draw_ground(self, screen: pygame.Surface, light: float) -> None:
        """Grass field below horizon (world-scrolled)."""
        night = 1.0 - light
        horizon_y = self.camera.world_to_screen(0, TownMap.GROUND_Y)[1]
        base = (
            int(42 * night + 72 * light),
            int(95 * night + 145 * light),
            int(32 * night + 78 * light),
        )
        dark = (
            int(base[0] * 0.85),
            int(base[1] * 0.85),
            int(base[2] * 0.85),
        )
        pygame.draw.rect(screen, base, (0, horizon_y, SCREEN_WIDTH, SCREEN_HEIGHT - horizon_y))
        # Subtle ground bands
        for band in range(horizon_y, SCREEN_HEIGHT, 24):
            if (band // 24) % 2 == 0:
                pygame.draw.line(screen, dark, (0, band), (SCREEN_WIDTH, band), 2)

    def _draw_zone_backgrounds(self, screen: pygame.Surface, light: float) -> None:
        for zone_id, zone in ZONES.items():
            bx, by, bw, bh = zone["bounds"]
            sx, sy = self.camera.world_to_screen(bx, by)
            rect = pygame.Rect(sx, sy, bw, bh)
            color = zone.get("color", (90, 130, 90))
            alpha = int(34 + 28 * light)
            fill = pygame.Surface((max(1, rect.width), max(1, rect.height)), pygame.SRCALPHA)
            pygame.draw.rect(fill, (*color, alpha), fill.get_rect(), border_radius=18)
            pygame.draw.rect(fill, (*color, min(170, alpha + 80)), fill.get_rect(), 3, border_radius=18)
            screen.blit(fill, rect.topleft)

            label = self.font_small.render(str(zone["name"]), True, (235, 240, 248))
            shadow = self.font_small.render(str(zone["name"]), True, (0, 0, 0))
            label_pos = (rect.x + 16, rect.y + 12)
            screen.blit(shadow, (label_pos[0] + 1, label_pos[1] + 1))
            screen.blit(label, label_pos)

    def _draw_scenic_details(self, screen: pygame.Surface, light: float) -> None:
        # Hangar runway and fuel pads
        runway = pygame.Rect(90, 845, 510, 70)
        sx, sy = self.camera.world_to_screen(runway.x, runway.y)
        rr = pygame.Rect(sx, sy, runway.width, runway.height)
        pygame.draw.rect(screen, (62, 66, 72), rr, border_radius=6)
        pygame.draw.rect(screen, (98, 104, 112), rr, 2, border_radius=6)
        for x in range(rr.x + 28, rr.right - 20, 70):
            pygame.draw.line(screen, (240, 220, 120), (x, rr.centery), (x + 34, rr.centery), 3)

        # Research observatory pad
        cx, cy = self.camera.world_to_screen(1450, 420)
        pygame.draw.circle(screen, (190, 202, 210), (cx, cy), 34)
        pygame.draw.circle(screen, (80, 110, 140), (cx, cy), 34, 3)
        pygame.draw.arc(screen, (210, 230, 245), (cx - 28, cy - 36, 56, 52), 3.3, 6.1, 4)

        # Plaza pond and flower ring
        pond_x, pond_y = self.camera.world_to_screen(900, 745)
        pond = pygame.Surface((140, 74), pygame.SRCALPHA)
        pygame.draw.ellipse(pond, (54, 126, 168, 190), pond.get_rect())
        pygame.draw.ellipse(pond, (150, 210, 235, 110), pond.get_rect().inflate(-20, -24), 2)
        screen.blit(pond, (pond_x - 70, pond_y - 37))
        for i in range(12):
            ang = i * 0.52
            fx = pond_x + int(math.cos(ang) * 82)
            fy = pond_y + int(math.sin(ang) * 46)
            pygame.draw.circle(screen, (255, 228, 80), (fx, fy), 3)

        # Mission control antenna array
        for wx, wy, h in ((485, 400, 48), (520, 430, 34), (760, 405, 58)):
            ax, ay = self.camera.world_to_screen(wx, wy)
            pygame.draw.line(screen, (190, 198, 210), (ax, ay), (ax, ay - h), 3)
            pygame.draw.circle(screen, (255, 236, 120), (ax, ay - h), 5)
            pygame.draw.arc(screen, (180, 210, 240), (ax - 24, ay - h - 18, 48, 34), 3.8, 5.7, 2)

        # Supply yard crates
        for wx, wy, color in (
            (1135, 900, (150, 92, 56)),
            (1178, 900, (120, 100, 80)),
            (1370, 875, (160, 118, 68)),
            (1414, 875, (120, 100, 80)),
        ):
            bx, by = self.camera.world_to_screen(wx, wy)
            box = pygame.Rect(bx, by - 28, 34, 28)
            pygame.draw.rect(screen, color, box, border_radius=3)
            pygame.draw.rect(screen, (70, 58, 48), box, 2, border_radius=3)

    def _draw_paths(self, screen: pygame.Surface, light: float) -> None:
        self.road_renderer.draw_network(screen, self.camera.world_to_screen, self.path_routes, light=light)

    def _draw_buildings(self, screen: pygame.Surface, is_night: bool) -> None:
        ordered = sorted(self.buildings, key=lambda b: b.rect.bottom)
        for building in ordered:
            render_type = self._building_render_type(building)
            base_w, _ = BuildingRenderer.BASE_SIZES.get(render_type, (100, 80))
            scale = building.rect.width / base_w
            sx, sy = self.camera.world_to_screen(building.rect.x, building.rect.bottom)
            visual_rect = self.building_renderer.draw_at(
                screen,
                render_type,
                sx,
                sy,
                scale=scale,
                anchor_bottom=True,
                is_night=is_night,
            )
            label_color = HOME_LABEL_COLORS.get(render_type, (255, 255, 255))
            label = self.font_small.render(building.name, True, label_color)
            label_rect = label.get_rect(center=(visual_rect.centerx, visual_rect.bottom + 14))
            pygame.draw.rect(
                screen,
                (18, 22, 30),
                label_rect.inflate(10, 6),
                border_radius=4,
            )
            screen.blit(label, label_rect)
            if self._near_building(building):
                hint = "Press to enter" if building.action.startswith("npc_home:") else "Your home"
                if building.action == "house":
                    hint = "Press to enter"
                self._draw_world_label(screen, visual_rect.centerx, visual_rect.top - 10, hint)

    def _draw_mailbox(self, screen: pygame.Surface) -> None:
        sx, sy = self.camera.world_to_screen(self.mailbox_rect.x, self.mailbox_rect.y)
        rect = pygame.Rect(sx, sy, self.mailbox_rect.width, self.mailbox_rect.height)
        pygame.draw.rect(screen, (102, 76, 52), (rect.centerx - 3, rect.y + 18, 6, 30))
        box = pygame.Rect(rect.x + 2, rect.y + 4, rect.width - 4, 22)
        pygame.draw.rect(screen, (160, 40, 45), box, border_radius=6)
        pygame.draw.rect(screen, (78, 28, 32), box, 2, border_radius=6)
        pygame.draw.circle(screen, (235, 238, 242), (box.x + 8, box.centery), 3)
        unread = self._unread_mail_count()
        if unread:
            pygame.draw.line(screen, (240, 220, 70), (box.right - 4, box.y + 3), (box.right + 16, box.y - 12), 4)
            pygame.draw.rect(screen, (255, 236, 39), (box.right + 10, box.y - 24, 26, 18), border_radius=3)
            badge = self.font_small.render(str(unread), True, (20, 24, 32))
            screen.blit(badge, badge.get_rect(center=(box.right + 23, box.y - 15)))
        if self._near_mailbox():
            self._draw_world_label(screen, self.mailbox_rect.centerx, self.mailbox_rect.y - 18, "Press E for Mail")

    def _draw_world_label(self, screen: pygame.Surface, wx: float, wy: float, text: str) -> None:
        surf = self.font_small.render(text, True, (255, 255, 220))
        x, y = self.camera.world_to_screen(wx, wy)
        rect = surf.get_rect(center=(x, y))
        pygame.draw.rect(screen, (20, 24, 36), rect.inflate(12, 8), border_radius=4)
        screen.blit(surf, rect)

    def _draw_player(self, screen: pygame.Surface) -> None:
        x, y = self.camera.world_to_screen(self.player_x, self.player_y)
        pygame.draw.circle(screen, (20, 24, 32), (x, y), 13)
        pygame.draw.polygon(screen, self.session.player_color, [(x, y - 14), (x - 11, y + 10), (x + 11, y + 10)])

    def _draw_hud(self, screen: pygame.Surface, light: float) -> None:
        money = self.font_title.render(f"${self.session.money:,}", True, (255, 236, 39))
        pygame.draw.rect(screen, (18, 22, 30), (16, 16, 190, 40), border_radius=4)
        screen.blit(money, (28, 24))

        date = self.font.render(self.session.time.formatted(), True, (255, 255, 255))
        rect = date.get_rect(topright=(SCREEN_WIDTH - 26, 24))
        pygame.draw.rect(screen, (18, 22, 30), rect.inflate(24, 14), border_radius=4)
        screen.blit(date, rect)

        zone_name = get_zone_at(self.player_x, self.player_y)
        zn = self.font_small.render(ZONES[zone_name]["name"], True, (180, 200, 230))
        screen.blit(zn, (28, 62))

        period = "Daytime" if self.session.time.is_daytime() else "Night"
        period_surf = self.font_small.render(period, True, (255, 220, 120) if light > 0.5 else (140, 160, 220))
        screen.blit(period_surf, (SCREEN_WIDTH - 130, 62))

        rep = self.font_small.render(f"Rep {self.session.reputation}", True, (180, 220, 255))
        screen.blit(rep, (SCREEN_WIDTH - 130, 84))
        self._draw_team_morale(screen)

        mouse = pygame.mouse.get_pos()
        for rect, label, action in self.quick_buttons:
            hover = rect.collidepoint(mouse)
            pygame.draw.rect(screen, (54, 62, 82) if hover else (28, 34, 48), rect, border_radius=4)
            text = self.font.render(label, True, (255, 236, 39) if hover else (240, 244, 255))
            screen.blit(text, text.get_rect(center=rect.center))
        self._draw_minimap(screen)

    def _draw_team_morale(self, screen: pygame.Surface) -> None:
        labels = [
            ("Dr. Chen", "dr_chen", (110, 210, 255)),
            ("Bob", "bob", (255, 170, 70)),
            ("Maria", "maria", (255, 110, 150)),
            ("Jenkins", "jenkins", (180, 170, 140)),
        ]
        x = 16
        y = 98
        for name, key, color in labels:
            value = int(self.session.npc_morale.get(key, 5))
            mood = self.story_manager.morale_label(key)
            text = f"{name}: {value}/10 ({mood})"
            surf = self.font_small.render(text, True, color)
            pygame.draw.rect(screen, (18, 22, 30), (x - 4, y - 2, surf.get_width() + 8, 18), border_radius=3)
            screen.blit(surf, (x, y))
            y += 20

    def _draw_notice(self, screen: pygame.Surface, text: str) -> None:
        surf = self.font.render(text, True, (255, 236, 39))
        rect = surf.get_rect(center=(SCREEN_WIDTH // 2, 32))
        pygame.draw.rect(screen, (18, 22, 30), rect.inflate(24, 12), border_radius=4)
        screen.blit(surf, rect)

    def _draw_mailbox_overlay(self, screen: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))
        panel = pygame.Rect(0, 0, 720, 500)
        panel.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        pygame.draw.rect(screen, (26, 30, 42), panel, border_radius=10)
        pygame.draw.rect(screen, (120, 132, 160), panel, 2, border_radius=10)

        title = self.font_title.render("Mailbox", True, (255, 236, 39))
        screen.blit(title, (panel.x + 24, panel.y + 18))
        close_rect = pygame.Rect(panel.right - 96, panel.y + 18, 72, 32)
        pygame.draw.rect(screen, (54, 62, 82), close_rect, border_radius=4)
        close = self.font_small.render("Close", True, (240, 244, 255))
        screen.blit(close, close.get_rect(center=close_rect.center))

        if not self.session.mailbox:
            empty = self.font.render("No mail yet.", True, (190, 200, 218))
            screen.blit(empty, empty.get_rect(center=panel.center))
            return

        visible = self.session.mailbox[self.mail_scroll : self.mail_scroll + 3]
        y = panel.y + 70
        for mail in visible:
            card = pygame.Rect(panel.x + 24, y, panel.width - 48, 122)
            pygame.draw.rect(screen, (242, 236, 214), card, border_radius=6)
            pygame.draw.rect(screen, (160, 142, 108), card, 2, border_radius=6)
            sender = self.font.render(f"From: {mail.get('from', 'Unknown')}", True, (52, 44, 34))
            subject = self.font.render(str(mail.get("subject", "Letter")), True, (70, 56, 38))
            screen.blit(sender, (card.x + 18, card.y + 12))
            screen.blit(subject, (card.x + 18, card.y + 38))
            body_y = card.y + 68
            for line in wrap_text(str(mail.get("body", "")), self.font_small, card.width - 36)[:2]:
                body = self.font_small.render(line, True, (82, 72, 56))
                screen.blit(body, (card.x + 18, body_y))
                body_y += 20
            day = self.font_small.render(f"Day {mail.get('day', 1)}", True, (112, 96, 74))
            screen.blit(day, (card.right - day.get_width() - 18, card.y + 14))
            y += 132

        if len(self.session.mailbox) > 3:
            hint = self.font_small.render("Mouse wheel to scroll", True, (180, 190, 210))
            screen.blit(hint, (panel.x + 24, panel.bottom - 28))

    def _map_area(self, rect: pygame.Rect) -> Tuple[pygame.Rect, float]:
        if rect.height < 220:
            area = pygame.Rect(rect.x + 10, rect.y + 34, rect.width - 20, rect.height - 44)
        else:
            area = pygame.Rect(rect.x + 28, rect.y + 62, rect.width - 56, rect.height - 100)
        scale = min(area.width / self.bounds[0], area.height / self.bounds[1])
        return area, scale

    def _world_to_map(self, wx: float, wy: float, area: pygame.Rect, scale: float) -> Tuple[int, int]:
        offset_x = area.x + (area.width - self.bounds[0] * scale) / 2
        offset_y = area.y + (area.height - self.bounds[1] * scale) / 2
        return int(offset_x + wx * scale), int(offset_y + wy * scale)

    def _draw_map_contents(self, screen: pygame.Surface, area: pygame.Rect, scale: float, label_zones: bool) -> None:
        offset_x = area.x + (area.width - self.bounds[0] * scale) / 2
        offset_y = area.y + (area.height - self.bounds[1] * scale) / 2
        world_rect = pygame.Rect(int(offset_x), int(offset_y), int(self.bounds[0] * scale), int(self.bounds[1] * scale))
        pygame.draw.rect(screen, (50, 94, 56), world_rect, border_radius=4)
        pygame.draw.rect(screen, (108, 132, 116), world_rect, 2, border_radius=4)

        for zone_id, zone in ZONES.items():
            bx, by, bw, bh = zone["bounds"]
            rect = pygame.Rect(int(offset_x + bx * scale), int(offset_y + by * scale), int(bw * scale), int(bh * scale))
            pygame.draw.rect(screen, zone.get("color", (90, 130, 90)), rect, border_radius=4)
            pygame.draw.rect(screen, (235, 238, 246), rect, 1, border_radius=4)
            if label_zones:
                label = self.font_small.render(str(zone["name"]), True, (255, 255, 255))
                screen.blit(label, (rect.x + 6, rect.y + 5))

        for route in self.path_routes:
            pts = [self._world_to_map(x, y, area, scale) for x, y in route]
            if len(pts) >= 2:
                pygame.draw.lines(screen, (72, 70, 66), False, pts, max(4, int(12 * scale)))
                pygame.draw.lines(screen, (200, 188, 150), False, pts, max(2, int(6 * scale)))

        for building in self.buildings:
            b = building.rect
            rect = pygame.Rect(int(offset_x + b.x * scale), int(offset_y + b.y * scale), max(3, int(b.width * scale)), max(3, int(b.height * scale)))
            render_type = self._building_render_type(building)
            color = HOME_LABEL_COLORS.get(render_type, (200, 200, 200))
            if building.action.startswith("npc_home:") or building.action == "house":
                pygame.draw.rect(screen, color, rect, border_radius=2)
                pygame.draw.rect(screen, (20, 24, 32), rect, 1, border_radius=2)
            else:
                pygame.draw.rect(screen, (28, 32, 44), rect)
                pygame.draw.rect(screen, (255, 255, 255), rect, 1)

        px, py = self._world_to_map(self.player_x, self.player_y, area, scale)
        pygame.draw.circle(screen, (255, 236, 39), (px, py), 5 if label_zones else 3)
        pygame.draw.circle(screen, (20, 24, 32), (px, py), 5 if label_zones else 3, 1)

    def _draw_minimap(self, screen: pygame.Surface) -> None:
        rect = pygame.Rect(SCREEN_WIDTH - 282, 86, 250, 166)
        pygame.draw.rect(screen, (18, 22, 30), rect, border_radius=6)
        pygame.draw.rect(screen, (86, 98, 124), rect, 2, border_radius=6)
        title = self.font_small.render("Map  M", True, (220, 228, 244))
        screen.blit(title, (rect.x + 12, rect.y + 10))
        area, scale = self._map_area(rect)
        self._draw_map_contents(screen, area, scale, label_zones=False)

    def _draw_full_map(self, screen: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 168))
        screen.blit(overlay, (0, 0))
        rect = pygame.Rect(0, 0, 930, 560)
        rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        pygame.draw.rect(screen, (22, 27, 38), rect, border_radius=10)
        pygame.draw.rect(screen, (118, 132, 164), rect, 2, border_radius=10)
        title = self.font_title.render("Town Map", True, (255, 236, 39))
        screen.blit(title, (rect.x + 24, rect.y + 20))
        hint = self.font_small.render("Click a district to walk there | M or ESC close", True, (190, 200, 218))
        screen.blit(hint, (rect.right - hint.get_width() - 24, rect.y + 30))
        area, scale = self._map_area(rect)
        self._draw_map_contents(screen, area, scale, label_zones=True)

    def _handle_map_click(self, pos: Tuple[int, int]) -> None:
        rect = pygame.Rect(0, 0, 930, 560)
        rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        area, scale = self._map_area(rect)
        if not area.collidepoint(pos):
            self.map_open = False
            return
        offset_x = area.x + (area.width - self.bounds[0] * scale) / 2
        offset_y = area.y + (area.height - self.bounds[1] * scale) / 2
        wx = (pos[0] - offset_x) / scale
        wy = (pos[1] - offset_y) / scale
        for zone_id, zone in ZONES.items():
            bx, by, bw, bh = zone["bounds"]
            if bx <= wx <= bx + bw and by <= wy <= by + bh:
                self._set_target_to_zone(zone_id)
                self.map_open = False
                self.notice = f"{zone['name']} marked."
                self.notice_timer = 2.0
                return
        self.player_target_x, self.player_target_y = self.town_map.clamp_to_walkable(wx, wy)
        self.map_open = False
