from __future__ import annotations

import logging
import subprocess
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from portfwd.kube.process import PortForwardProcess

logger = logging.getLogger(__name__)

console = Console(stderr=True)


def make_table(
    processes: list[PortForwardProcess],
    statuses: dict[str, str],
    context: str | None,
) -> Table:
    context_str = f" [dim]({context})[/dim]" if context else ""
    table = Table(
        title=f"[bold]Port Forwards[/bold]{context_str}",
        caption="[dim]Press [bold]Ctrl+C[/bold] to stop[/dim]",
        border_style="bright_black",
        show_lines=False,
    )
    table.add_column("Namespace", style="cyan", no_wrap=True)
    table.add_column("Service", style="bold", no_wrap=True)
    table.add_column("Remote", style="cyan", justify="right")
    table.add_column("Local", style="cyan", justify="right")
    table.add_column("PID", style="dim", justify="right")
    table.add_column("Status")
    for fwd in processes:
        key = f"{fwd.service_name}:{fwd.remote_port}"
        raw = statuses.get(key, "live")
        if raw == "live":
            status = "[green]● live[/green]"
        elif raw == "stopped":
            status = "[yellow]■ stopped[/yellow]"
        else:
            status = f"[red]✗ {raw}[/red]"
        table.add_row(
            fwd.namespace,
            fwd.service_name,
            f":{fwd.remote_port}",
            f"localhost:{fwd.local_port}",
            str(fwd.process.pid),
            status,
        )
    return table


def print_error(e: subprocess.CalledProcessError, msg: str) -> None:
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
