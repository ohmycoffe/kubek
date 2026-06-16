from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SpecFileLine:
    line: int
    value: str


def load_spec_file(path: Path) -> list[SpecFileLine]:
    """Load port-forward service lines from a text file.

    Returns each non-empty, non-comment line with its 1-based file line number.
    Each line is expected to use the same format as ``--service``:
    ``[namespace/]name[:remote_port][::local_port]``.
    """
    lines: list[SpecFileLine] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            lines.append(SpecFileLine(line=line_no, value=stripped))
    return lines
