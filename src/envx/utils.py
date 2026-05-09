from __future__ import annotations

import base64
import datetime
import logging
import questionary
import typer

from envx.style import STYLE, console


def setup_logging(verbose: int) -> None:
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(verbose, len(levels) - 1)]
    logging.getLogger("envx").setLevel(level)


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


def resolve_namespace(value: str | None, available_namespaces: list[str]) -> str:
    if value:
        if value not in available_namespaces:
            console.print(f"[red]Error:[/red] namespace '{value}' not found.")
            raise typer.Exit(code=1)
        return value
    selected = questionary.select(
        "Select a namespace:",
        choices=available_namespaces,
        use_search_filter=True,
        use_jk_keys=False,
        style=STYLE,
    ).ask()
    if not selected:
        raise typer.Exit(code=0)
    return selected
