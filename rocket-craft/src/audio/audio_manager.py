"""Procedural SFX and MIDI music with silent fallback."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Dict, Optional, Sequence, Union

import numpy as np
import pygame

SAMPLE_RATE = 22050
CHANNELS = 2
BUFFER_SIZE = 512


def _write_simple_mid(path: Path, melody: Sequence[int], tempo: int = 520) -> None:
    def vlq(value: int) -> bytes:
        value = int(max(0, value))
        out = bytearray([value & 0x7F])
        value >>= 7
        while value:
            out.insert(0, (value & 0x7F) | 0x80)
            value >>= 7
        return bytes(out)

    def meta(delta: int, typ: int, data: bytes) -> bytes:
        return vlq(delta) + bytes([0xFF, typ]) + vlq(len(data)) + data

    def note_on(delta: int, note: int, velocity: int = 0x60) -> bytes:
        return vlq(delta) + bytes([0x90, note & 0x7F, velocity & 0x7F])

    def note_off(delta: int, note: int) -> bytes:
        return vlq(delta) + bytes([0x80, note & 0x7F, 0x40])

    track = bytearray()
    track.extend(meta(0, 0x51, struct.pack(">I", tempo * 1000)[1:]))
    track.extend(meta(0, 0x58, bytes([4, 2, 24, 8])))
    for i, pitch in enumerate(melody):
        track.extend(note_on(0 if i == 0 else 240, pitch))
        track.extend(note_off(240, pitch))
    track.extend(meta(240, 0x2F, b""))

    header = struct.pack(">4sIHHH", b"MThd", 6, 0, 1, 480)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + struct.pack(">4sI", b"MTrk", len(track)) + track)


def _ensure_music_file(path: Path) -> None:
    melodies = {
        "title_theme.mid": [60, 64, 67, 72],
        "town_plaza.mid": [67, 69, 72, 76],
        "town_hangar.mid": [48, 52, 55, 60],
        "town_research.mid": [72, 74, 77, 81],
    }
    if path.is_file() and path.name not in melodies:
        return
    _write_simple_mid(path, melodies.get(path.name, [60, 64, 67, 72]))


class AudioManager:
    """Audio facade that no-ops when pygame mixer is unavailable."""

    def __init__(self, assets_dir: Optional[Path] = None) -> None:
        self.enabled = False
        self._assets_dir = assets_dir or Path(__file__).resolve().parents[2] / "assets" / "audio"
        self._sfx: Dict[str, pygame.mixer.Sound] = {}
        self._sfx_channels: Dict[str, pygame.mixer.Channel] = {}
        self._current_music: Optional[str] = None
        self._error: Optional[str] = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(SAMPLE_RATE, size=-16, channels=CHANNELS, buffer=BUFFER_SIZE)
                pygame.mixer.init()
            pygame.mixer.set_num_channels(12)
            self._sfx["thrust"] = self.generate_thrust_sound()
            self._sfx["click"] = self.generate_click_sound()
            self._sfx["confirm"] = self.generate_click_sound(660.0, 0.08)
            self._sfx["error"] = self.generate_click_sound(180.0, 0.12)
            self.enabled = True
        except (pygame.error, ValueError, OSError) as exc:
            self._error = str(exc)
            self.enabled = False

    @property
    def error_message(self) -> Optional[str]:
        return self._error

    def _array_to_sound(self, samples: np.ndarray) -> pygame.mixer.Sound:
        pcm = (np.clip(samples, -1.0, 1.0) * 32767.0).astype(np.int16)
        return pygame.sndarray.make_sound(np.column_stack([pcm, pcm]))

    def generate_thrust_sound(self, duration: float = 0.45) -> pygame.mixer.Sound:
        n = max(2, int(SAMPLE_RATE * duration))
        rng = np.random.default_rng(42)
        noise = rng.uniform(-1.0, 1.0, n)
        kernel = np.ones(28) / 28.0
        filtered = np.convolve(noise, kernel, mode="same")
        t = np.linspace(0.0, duration, n, endpoint=False)
        rumble = 0.35 + 0.65 * (0.5 + 0.5 * np.sin(2.0 * np.pi * 14.0 * t))
        return self._array_to_sound((filtered * rumble * 0.55).astype(np.float32))

    def generate_click_sound(self, frequency: float = 880.0, duration: float = 0.06) -> pygame.mixer.Sound:
        n = max(2, int(SAMPLE_RATE * duration))
        t = np.linspace(0.0, duration, n, endpoint=False)
        wave = np.sin(2.0 * np.pi * frequency * t) * np.exp(-t * 55.0)
        return self._array_to_sound((wave * 0.7).astype(np.float32))

    def play_sfx(self, name: str, loop: bool = False, volume: float = 1.0) -> None:
        if not self.enabled:
            return
        sound = self._sfx.get(name)
        if sound is None:
            return
        try:
            channel = sound.play(loops=-1 if loop else 0)
            if channel is not None:
                channel.set_volume(max(0.0, min(1.0, volume)))
                if loop:
                    self._sfx_channels[name] = channel
        except pygame.error:
            pass

    def stop_sfx(self, name: str) -> None:
        if not self.enabled:
            return
        channel = self._sfx_channels.pop(name, None)
        if channel is not None:
            try:
                channel.stop()
            except pygame.error:
                pass

    def play_music(self, path: Union[Path, str], loop: bool = True, volume: float = 0.55, fade_ms: int = 0) -> None:
        if not self.enabled:
            return
        resolved = Path(path)
        _ensure_music_file(resolved)
        key = str(resolved.resolve())
        try:
            if self._current_music == key and pygame.mixer.music.get_busy():
                pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))
                return
            if fade_ms > 0 and pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(fade_ms)
            pygame.mixer.music.load(key)
            pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))
            pygame.mixer.music.play(-1 if loop else 0)
            self._current_music = key
        except (pygame.error, OSError):
            self._current_music = None

    def stop_music(self, fade_ms: int = 0) -> None:
        if not self.enabled:
            return
        try:
            pygame.mixer.music.fadeout(fade_ms) if fade_ms > 0 else pygame.mixer.music.stop()
            self._current_music = None
        except pygame.error:
            pass

    def title_music_path(self) -> Path:
        return self._assets_dir / "title_theme.mid"

    def zone_music_path(self, zone_id: str) -> Optional[Path]:
        from systems.town_zones import ZONES

        music = ZONES.get(zone_id, {}).get("music")
        return self._assets_dir / str(music) if music else None

    def update_launch_audio(self, throttle: float) -> None:
        if not self.enabled:
            return
        if throttle > 0.01:
            channel = self._sfx_channels.get("thrust")
            if channel is None or not channel.get_busy():
                self.play_sfx("thrust", loop=True, volume=0.35 + 0.45 * throttle)
            else:
                channel.set_volume(0.35 + 0.45 * throttle)
        else:
            self.stop_sfx("thrust")
