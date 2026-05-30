"""State machine for RocketCraft screens."""

from __future__ import annotations

from enum import Enum
from typing import Optional


class GameState(Enum):
    TITLE = 0
    INTRO = 1
    LOAD = 2
    CHARACTER = 3
    TOWN = 4
    HANGAR = 5
    LAUNCH = 6
    DIALOGUE = 7
    MENU = 8
    HOUSE = 9


class StateManager:
    """Tracks the active screen and the previous screen."""

    def __init__(self, initial: GameState = GameState.TITLE) -> None:
        self.current = initial
        self.previous: Optional[GameState] = None

    def switch(self, new_state: GameState) -> None:
        if new_state == self.current:
            return
        self.previous = self.current
        self.current = new_state
