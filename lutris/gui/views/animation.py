"""Small, frame-clock driven transitions for the desktop library."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Transition:
    start: float
    target: float
    started_at: float
    duration: float = 0.18

    def value_at(self, now: float) -> float:
        if self.duration <= 0:
            return self.target
        progress = min(1.0, max(0.0, (now - self.started_at) / self.duration))
        eased = 1.0 - (1.0 - progress) ** 3
        return self.start + (self.target - self.start) * eased

    def finished(self, now: float) -> bool:
        return now >= self.started_at + self.duration

    def retarget(self, target: float, now: float) -> "Transition":
        return Transition(self.value_at(now), target, now, self.duration)
