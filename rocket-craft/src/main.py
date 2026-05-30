"""RocketCraft entry point with screen/state management."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Optional

import pygame

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from audio import AudioManager  # noqa: E402
from config import FPS, SCREEN_HEIGHT, SCREEN_WIDTH  # noqa: E402
from core.game_session import GameSession  # noqa: E402
from core.game_state import GameState, StateManager  # noqa: E402
from core.save_load import SaveManager  # noqa: E402
from screens.character_screen import CharacterScreen  # noqa: E402
from screens.hangar_screen import HangarScreen  # noqa: E402
from screens.house_interior import HouseInteriorScreen  # noqa: E402
from screens.intro_cutscene import IntroCutscene  # noqa: E402
from screens.launch_screen import LaunchScreen  # noqa: E402
from screens.load_game_screen import LoadGameScreen  # noqa: E402
from screens.title_screen import TitleScreen  # noqa: E402
from screens.town_screen import TownScreen  # noqa: E402


def draw_fade(screen: pygame.Surface, alpha: int) -> None:
    if alpha <= 0:
        return
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, max(0, min(255, alpha))))
    screen.blit(overlay, (0, 0))


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("RocketCraft")
    clock = pygame.time.Clock()

    state = StateManager(GameState.TITLE)
    save_manager = SaveManager()
    session = GameSession()
    audio = AudioManager()

    launch_screen_active = False

    town_screen = TownScreen(session, audio=audio)
    screens: Dict[GameState, object] = {
        GameState.TITLE: TitleScreen(save_manager, audio=audio, session=session),
        GameState.LOAD: LoadGameScreen(save_manager, audio=audio),
        GameState.CHARACTER: CharacterScreen(session, audio=audio),
        GameState.TOWN: town_screen,
        GameState.HANGAR: HangarScreen(session, audio=audio, story_manager=town_screen.story_manager),
        GameState.HOUSE: HouseInteriorScreen(session, save_manager, audio=audio),
        GameState.LAUNCH: LaunchScreen(screen, audio=audio, session=session),
    }

    def rebuild_campaign_screens() -> None:
        town = TownScreen(session, audio=audio)
        screens[GameState.TOWN] = town
        screens[GameState.HANGAR] = HangarScreen(session, audio=audio, story_manager=town.story_manager)
        screens[GameState.HOUSE] = HouseInteriorScreen(session, save_manager, audio=audio)

    running = True
    fade_time = 1.0
    fade_duration = 1.0
    last_state: Optional[GameState] = None

    def switch_to(new_state: GameState, duration: float = 0.5) -> None:
        nonlocal fade_time, fade_duration
        state.switch(new_state)
        fade_duration = max(0.01, duration)
        fade_time = fade_duration

    def begin_launch(auto_ignite: bool = True) -> None:
        nonlocal launch_screen_active
        if launch_screen_active or state.current == GameState.LAUNCH:
            return
        screens[GameState.LAUNCH] = LaunchScreen(
            screen,
            audio=audio,
            session=session,
            auto_ignite=auto_ignite,
        )
        launch_screen_active = True
        switch_to(GameState.LAUNCH, 0.8)

    def autosave() -> None:
        save_manager.save("autosave", session.to_save_dict())

    while running:
        dt = clock.tick(FPS) / 1000.0
        active = screens[state.current]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            action = active.handle_event(event)  # type: ignore[attr-defined]
            if action == "quit":
                running = False
            elif action == "new_game":
                session.reset_new_game()
                launch_screen_active = False
                screens[GameState.INTRO] = IntroCutscene(audio=audio)
                switch_to(GameState.INTRO, 0.8)
            elif action == "intro_done":
                save_manager.set_intro_seen()
                screens[GameState.CHARACTER] = CharacterScreen(session, audio=audio)
                switch_to(GameState.CHARACTER, 0.6)
            elif action == "load_screen":
                screens[GameState.LOAD] = LoadGameScreen(save_manager, audio=audio)
                switch_to(GameState.LOAD, 0.4)
            elif action == "new_game_ready":
                launch_screen_active = False
                save_manager.set_current_slot("autosave")
                rebuild_campaign_screens()
                switch_to(GameState.TOWN, 1.0)
            elif isinstance(action, str) and action.startswith("load_game:"):
                filename = action.split(":", 1)[1]
                try:
                    data = save_manager.load(filename)
                    session.apply_save(data)
                    save_manager.set_current_slot(filename)
                    launch_screen_active = False
                    rebuild_campaign_screens()
                    town = screens[GameState.TOWN]
                    if isinstance(town, TownScreen):
                        town.refresh_building_labels()
                    switch_to(GameState.TOWN, 0.8)
                except OSError:
                    pass
            elif action == "load_game":
                try:
                    data = save_manager.load("autosave")
                    session.apply_save(data)
                    save_manager.set_current_slot("autosave")
                    launch_screen_active = False
                    rebuild_campaign_screens()
                    town = screens[GameState.TOWN]
                    if isinstance(town, TownScreen):
                        town.refresh_building_labels()
                    switch_to(GameState.TOWN, 0.8)
                except OSError:
                    switch_to(GameState.LOAD, 0.4)
            elif action == "title":
                launch_screen_active = False
                switch_to(GameState.TITLE, 0.5)
            elif action == "town":
                launch_screen_active = False
                switch_to(GameState.TOWN, 0.5)
            elif action == "hangar":
                hangar = screens.get(GameState.HANGAR)
                if isinstance(hangar, HangarScreen):
                    hangar.on_enter()
                switch_to(GameState.HANGAR, 0.5)
            elif action == "house":
                house = screens.get(GameState.HOUSE)
                if isinstance(house, HouseInteriorScreen):
                    house.on_enter()
                switch_to(GameState.HOUSE, 0.5)
            elif isinstance(action, str) and action.startswith("npc_home:"):
                owner_name = action.split(":", 1)[1]
                owner_key = {
                    "Dr. Chen": "dr_chen",
                    "Bob": "bob",
                    "Maria": "maria",
                    "Old Man Jenkins": "jenkins",
                }.get(owner_name, "npc")
                house = screens.get(GameState.HOUSE)
                if isinstance(house, HouseInteriorScreen):
                    house.on_enter(owner_name=owner_name, owner_key=owner_key)
                switch_to(GameState.HOUSE, 0.5)
            elif action == "launch":
                begin_launch(auto_ignite=True)

        active = screens[state.current]
        active.update(dt)  # type: ignore[attr-defined]

        if state.current == GameState.INTRO and isinstance(active, IntroCutscene) and active.is_finished():
            save_manager.set_intro_seen()
            screens[GameState.CHARACTER] = CharacterScreen(session, audio=audio)
            switch_to(GameState.CHARACTER, 0.6)
            active = screens[state.current]

        hangar = screens.get(GameState.HANGAR)
        if state.current == GameState.HANGAR and hangar is not None and getattr(hangar, "pending_launch", False):
            hangar.pending_launch = False
            begin_launch(auto_ignite=True)

        if state.current == GameState.TOWN and isinstance(active, TownScreen):
            if not active._town_entered:
                active.on_enter()
            deferred = active.consume_deferred_action()
            if deferred == "hangar":
                hangar = screens.get(GameState.HANGAR)
                if isinstance(hangar, HangarScreen):
                    hangar.on_enter()
                switch_to(GameState.HANGAR, 0.35)
            elif deferred == "house":
                house = screens.get(GameState.HOUSE)
                if isinstance(house, HouseInteriorScreen):
                    house.on_enter()
                switch_to(GameState.HOUSE, 0.35)

        active.draw(screen)  # type: ignore[attr-defined]

        if fade_time > 0.0:
            fade_time = max(0.0, fade_time - dt)
            draw_fade(screen, int(255 * (fade_time / fade_duration)))

        if state.current != last_state:
            if last_state == GameState.LAUNCH:
                audio.stop_sfx("thrust")
                launch_screen_active = False

            if state.current in (GameState.TITLE, GameState.LOAD):
                audio.play_music(audio.title_music_path())
            elif state.current == GameState.INTRO:
                audio.play_music(audio.title_music_path(), fade_ms=800)
            elif state.current == GameState.TOWN:
                town = screens[GameState.TOWN]
                if isinstance(town, TownScreen):
                    path = audio.zone_music_path(town.current_zone)
                    if path:
                        audio.play_music(path, fade_ms=800)
            elif state.current == GameState.HANGAR:
                path = audio.zone_music_path("hangar_area")
                if path:
                    audio.play_music(path, fade_ms=600)
            elif state.current == GameState.HOUSE:
                path = audio.zone_music_path("hangar_area")
                if path:
                    audio.play_music(path, fade_ms=600)
            elif state.current == GameState.LAUNCH:
                audio.stop_music(fade_ms=300)
            last_state = state.current
            if state.current in (GameState.TOWN, GameState.HANGAR, GameState.HOUSE, GameState.LAUNCH):
                autosave()

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
