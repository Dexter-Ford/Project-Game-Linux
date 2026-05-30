"""Font helpers with Thai-capable fallbacks."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

import pygame

_THAI_SAMPLE = "กขคไทย"
_THAI_FONT_NAMES = (
    "notosansthai",
    "notosansthailooped",
    "thonburi",
    "thonburiui",
    "sukhumvitset",
    "arialunicode",
    "tahoma",
    "garuda",
    "loma",
    "dejavusans",
)
_COMMON_THAI_FONT_PATHS = (
    "/System/Library/Fonts/Supplemental/Thonburi.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Tahoma.ttf",
    "/System/Library/Fonts/Supplemental/SukhumvitSet.ttc",
    "/usr/share/fonts/truetype/tlwg/Garuda.ttf",
    "/usr/share/fonts/truetype/tlwg/Loma.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
)


def _ensure_font_module() -> None:
    if not pygame.font.get_init():
        pygame.font.init()


def _normalise(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _supports(font: pygame.font.Font, text: str) -> bool:
    try:
        metrics = font.metrics(text)
    except (pygame.error, UnicodeError):
        return False
    return bool(metrics) and all(item is not None for item in metrics)


def _candidate_paths() -> Iterable[str]:
    available = {_normalise(name): name for name in pygame.font.get_fonts()}
    for wanted in _THAI_FONT_NAMES:
        actual = available.get(wanted)
        if actual:
            path = pygame.font.match_font(actual)
            if path:
                yield path
    for wanted in _THAI_FONT_NAMES:
        path = pygame.font.match_font(wanted)
        if path:
            yield path
    for path in _COMMON_THAI_FONT_PATHS:
        if Path(path).is_file():
            yield path


@lru_cache(maxsize=1)
def _thai_font_path() -> Optional[str]:
    _ensure_font_module()
    seen = set()
    for path in _candidate_paths():
        if path in seen:
            continue
        seen.add(path)
        try:
            font = pygame.font.Font(path, 18)
        except (OSError, pygame.error):
            continue
        if _supports(font, _THAI_SAMPLE):
            return path
    return None


def get_game_font(size: int, bold: bool = False) -> pygame.font.Font:
    _ensure_font_module()
    path = _thai_font_path()
    if path:
        font = pygame.font.Font(path, size)
        font.set_bold(bold)
        return font
    return pygame.font.SysFont("consolas", size, bold=bold)


def get_dialogue_font(size: int, bold: bool = False) -> pygame.font.Font:
    return get_game_font(size, bold=bold)
