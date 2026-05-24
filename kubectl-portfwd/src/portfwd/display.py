from __future__ import annotations

from dataclasses import dataclass

from rich.table import Table

from portfwd.kubectl import PortForwardProcess


@dataclass
class _Row:
    process: PortForwardProcess
    status: str = "notset"


class LiveStatusTable:
    """Owns per-process status state and renders it as a Rich `Table`.

    Encapsulates the row-key scheme so callers never deal with strings.
    """

    def __init__(self, context: str | None = None) -> None:
        self.__context = context
        self.__rows: dict[str, _Row] = {}

    @staticmethod
    def __key(p: PortForwardProcess) -> str:
        return f"{p.namespace}/{p.service_name}:{p.remote_port}"

    def track(self, process: PortForwardProcess) -> None:
        """Register a freshly started subprocess as 'live'."""
        if process.process.returncode is None:
            status = "live"
        else:
            status = f"died (exit {process.process.returncode})"
        self.__rows[self.__key(process)] = _Row(process=process, status=status)

    def mark_died(self, process: PortForwardProcess) -> None:
        """Mark a tracked subprocess as dead and record its exit code."""
        if process.process.returncode is None:
            raise ValueError("Process is still live")
        row = self.__rows.get(self.__key(process))
        if row is not None:
            row.status = f"died (exit {process.process.returncode})"

    def mark_stopped(self, process: PortForwardProcess) -> None:
        """Mark a tracked subprocess as cleanly stopped."""
        if process.process.returncode is None:
            raise ValueError("Process is still live")
        row = self.__rows.get(self.__key(process))
        if row is not None:
            row.status = "stopped"

    def render(self) -> Table:
        """Render the current state as a Rich `Table`."""
        context_str = f" [dim]({self.__context})[/dim]" if self.__context else ""
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
        for row in self.__rows.values():
            p = row.process
            if row.status == "live":
                status_cell = "[green]● live[/green]"
            elif row.status == "stopped":
                status_cell = "[yellow]■ stopped[/yellow]"
            else:
                status_cell = f"[red]✗ {row.status}[/red]"
            table.add_row(
                p.namespace,
                p.service_name,
                f":{p.remote_port}",
                f"localhost:{p.local_port}",
                str(p.process.pid),
                status_cell,
            )
        return table
