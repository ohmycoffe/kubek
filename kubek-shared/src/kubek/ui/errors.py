from __future__ import annotations

import logging
import subprocess

from rich.console import Console
from rich.panel import Panel

logger = logging.getLogger(__name__)

console = Console(stderr=True)


def print_error(e: subprocess.CalledProcessError, msg: str) -> None:
    """Display a subprocess error in a Rich Panel.

    Args:
        e: CalledProcessError from subprocess call.
        msg: Header message for the error panel.
    """
    stderr = (e.stderr or "").strip()
    logger.error("Command %s failed [%s]: %s", " ".join(e.cmd), e.returncode, stderr)
    console.print(
        Panel(
            f"[red]{stderr or 'no output'}[/red]",
            title=f"[bold red]{msg}[/bold red]",
            border_style="red",
            expand=False,
        )
    )
