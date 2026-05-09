import logging
import subprocess

from questionary import Style
from rich.console import Console
from rich.panel import Panel

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
            f"[red]{stderr}[/red]",
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
            title=f"[bold red]{msg}[/bold red]",
            border_style="red",
            expand=False,
        )
    )


STYLE = Style(
    [
        ("qmark", "fg:#61afef bold"),
        ("question", "bold"),
        ("answer", "fg:#98c379 bold"),
        ("pointer", "fg:#61afef bold"),
        ("highlighted", "fg:#61afef bold"),
        ("selected", "fg:#98c379"),
        ("separator", "fg:#4b5263"),
        ("instruction", "fg:#4b5263"),
        ("text", ""),
        ("disabled", "fg:#4b5263 italic"),
    ]
)
