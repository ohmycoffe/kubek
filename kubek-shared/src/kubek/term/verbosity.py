from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Self


class VerbosityLevel(IntEnum):
    NORMAL = 0
    VERBOSE = 1
    DIAGNOSTIC = 2


@dataclass(frozen=True)
class Verbosity:
    level: VerbosityLevel

    @classmethod
    def from_count(cls, count: int) -> Self:
        if count <= 0:
            return cls(level=VerbosityLevel.NORMAL)

        if count == 1:
            return cls(level=VerbosityLevel.VERBOSE)

        return cls(level=VerbosityLevel.DIAGNOSTIC)

    def allows(self, required: VerbosityLevel) -> bool:
        return self.level.value >= required.value

    @property
    def show_tracebacks(self) -> bool:
        return self.level >= VerbosityLevel.DIAGNOSTIC
