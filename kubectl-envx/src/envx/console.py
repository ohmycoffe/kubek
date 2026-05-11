from __future__ import annotations

import logging
import subprocess

from rich.console import Console
from rich.panel import Panel

from envx.style import COLOR_ERROR

console = Console(stderr=True)

logger = logging.getLogger(__name__)


def print_error(e: subprocess.CalledProcessError, msg: str) -> None:
    logger.debug("kubectl error", exc_info=e, stack_info=True)
    stderr = (e.stderr or "no output").strip()
    stdout = (e.stdout or "no output").strip()
    cmd = " ".join(e.cmd)
    content = "\n".join(
        [
            "[dim]stderr:[/dim]",
            f"[{COLOR_ERROR}]{stderr}[/]",
            "",
            "[dim]stdout:[/dim]",
            stdout,
            "",
            f"[dim]command:[/dim] {cmd}",
            f"[dim]exit code:[/dim] {e.returncode}",
        ]
    )
    console.print(
        Panel(
            content,
            title=f"[bold {COLOR_ERROR}]{msg}[/]",
            border_style=COLOR_ERROR,
            expand=False,
        )
    )
