"""Stardew-like in-game day/night clock."""

from __future__ import annotations


DAY_START_HOUR = 6
DAY_END_HOUR = 2
DAY_SPAN_MINUTES = 20 * 60


class TimeSystem:
    """Day starts at 6 AM and rolls to the next day at 2 AM.

    ``day_length_seconds`` makes the active 20-hour day adjustable. The default
    is 10 real minutes per in-game day.
    """

    def __init__(
        self,
        day: int = 1,
        hour: int = DAY_START_HOUR,
        minute: float = 0.0,
        time_speed: float = 1.0,
        day_length_seconds: float = 600.0,
    ) -> None:
        self.day = day
        self.hour = hour
        self.minute = minute
        self.time_speed = time_speed
        self.day_length_seconds = max(60.0, day_length_seconds)
        self.paused = False

    def update(self, dt: float) -> bool:
        """Advance clock. Returns True when the calendar rolls to a new day."""
        if self.paused:
            return False
        minutes_per_real_second = DAY_SPAN_MINUTES / self.day_length_seconds
        self.minute += dt * minutes_per_real_second * self.time_speed
        rolled = False
        while self.minute >= 60.0:
            self.minute -= 60.0
            self.hour += 1
            if self.hour >= 24:
                self.hour -= 24
            if self.hour == DAY_END_HOUR:
                self.start_next_day()
                rolled = True
                break
        return rolled

    def start_next_day(self) -> None:
        self.day += 1
        self.hour = DAY_START_HOUR
        self.minute = 0.0

    def is_daytime(self) -> bool:
        return 6 <= self.hour < 18

    def get_light_level(self) -> float:
        if 6 <= self.hour < 12:
            return (self.hour - 6 + self.minute / 60.0) / 6.0
        if 12 <= self.hour < 18:
            return 1.0 - (self.hour - 12 + self.minute / 60.0) / 6.0
        return 0.2

    def sleep_until_morning(self) -> None:
        """Skip the rest of the night and start the next morning."""
        self.start_next_day()

    def formatted(self) -> str:
        suffix = "AM" if self.hour < 12 else "PM"
        hour = self.hour % 12 or 12
        return f"Day {self.day}  {hour}:{int(self.minute):02d} {suffix}"

    @classmethod
    def from_dict(cls, data: dict) -> "TimeSystem":
        return cls(
            day=int(data.get("day", 1)),
            hour=int(data.get("hour", DAY_START_HOUR)),
            minute=float(data.get("minute", 0.0)),
            time_speed=float(data.get("time_speed", 1.0)),
            day_length_seconds=float(data.get("day_length_seconds", 600.0)),
        )
