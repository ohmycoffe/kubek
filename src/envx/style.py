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


# fmt: off
COLOR_ACCENT  = "#e5c07b"  # yellow     — draws attention (qmark)
COLOR_SUCCESS = "#98c379"  # green      — confirmed / selected
COLOR_ACTIVE  = "#61afef"  # blue       — navigation / pointer
COLOR_ERROR   = "#e06c75"  # red        — errors / failures
COLOR_MUTED   = "#5c6370"  # gray       — secondary elements
COLOR_SUBTLE  = "#4b5263"  # dark gray  — near-invisible hints

# fmt: off
STYLE = Style(
    [
        ("qmark",       f"fg:{COLOR_ACCENT} bold"),
        ("question",    "bold"),
        ("answer",      f"fg:{COLOR_SUCCESS} bold"),
        ("pointer",     f"fg:{COLOR_ACTIVE} bold"),
        ("highlighted", f"fg:{COLOR_ACTIVE} bold"),
        ("selected",    f"fg:{COLOR_SUCCESS}"),
        ("separator",   f"fg:{COLOR_MUTED}"),
        ("instruction", f"fg:{COLOR_SUBTLE} italic"),
        ("text",        ""),
        ("disabled",    f"fg:{COLOR_SUBTLE} italic"),
    ]
)
# fmt: on
