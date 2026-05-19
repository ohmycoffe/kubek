from __future__ import annotations

import logging
from subprocess import CalledProcessError

from rich.panel import Panel
from rich.text import Text

from kubek.kube.client import KubectlError
from kubek.term.console import get_console
from kubek.term.style import Color, Icon, RichStyle

logger = logging.getLogger(__name__)


console = get_console()


def print_error(e: KubectlError | CalledProcessError, msg: str) -> None:
    stderr = (e.stderr or "no output").strip()
    stdout = (e.stdout or "no output").strip()
    cmd = " ".join(e.cmd)
    content = "\n".join(
        [
            "[dim]stderr:[/dim]",
            f"[{Color.ERROR}]{stderr}[/]",
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
            title=Text(f"{Icon.FATAL} {msg}", style=RichStyle.ERROR),
            border_style=Color.ERROR,
            expand=False,
        )
    )
