from __future__ import annotations

import datetime

from kubek.term import setup_logging as _setup_logging


def setup_logging(verbose: int) -> None:
    _setup_logging(verbose, "export_dotenv", "kubek")


def export_as_dotenv(vals: dict[str, str], name: str | None = None) -> str:
    sorted_list = sorted(vals.items(), key=lambda x: x[0])
    res = []
    if name:
        now = datetime.datetime.now().isoformat(timespec="seconds")
        res.append(f"# {name} @ {now}")
    for key, value in sorted_list:
        res.append(f"{key}={value}")
    return "\n".join(res)
