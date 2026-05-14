from __future__ import annotations

import base64
import datetime
import logging


def setup_logging(verbose: int) -> None:
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(verbose, len(levels) - 1)]
    logging.getLogger("kenvx").setLevel(level)


def decode(val: str) -> str:
    decoded_bytes = base64.b64decode(val)
    return decoded_bytes.decode("utf-8")


def export_as_dotenv(vals: dict[str, str], name: str | None = None) -> str:
    sorted_list = sorted(vals.items(), key=lambda x: x[0])
    res = []
    if name:
        now = datetime.datetime.now().isoformat(timespec="seconds")
        res.append(f"# {name} @ {now}")
    for key, value in sorted_list:
        res.append(f"{key}={value}")
    return "\n".join(res)
