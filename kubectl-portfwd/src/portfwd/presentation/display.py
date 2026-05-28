from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from rich.table import Table

from portfwd.application.port_forwarding.events import PortForwardProcessSnapshot


class PortForwardStatus(StrEnum):
    LIVE = "live"
    STOPPED = "stopped"
    DIED = "died"


@dataclass(frozen=True)
class PortForwardRowKey:
    namespace: str
    service_name: str
    remote_port: int
    local_port: int
    pid: int

    @classmethod
    def from_snapshot(
        cls,
        snapshot: PortForwardProcessSnapshot,
    ) -> PortForwardRowKey:
        return cls(
            namespace=snapshot.namespace,
            service_name=snapshot.service_name,
            remote_port=snapshot.remote_port,
            local_port=snapshot.local_port,
            pid=snapshot.pid,
        )


@dataclass
class _Row:
    key: PortForwardRowKey
    status: PortForwardStatus
    returncode: int | None = None


class LiveStatusTable:
    """Owns per-process status state and renders it as a Rich `Table`.

    Encapsulates the row-key scheme so callers never deal with strings.
    """

    def __init__(self, context: str | None = None) -> None:
        self.__context = context
        self.__rows: dict[PortForwardRowKey, _Row] = {}

    def track(self, snapshot: PortForwardProcessSnapshot) -> None:
        key = PortForwardRowKey.from_snapshot(snapshot)

        self.__rows[key] = _Row(
            key=key,
            status=PortForwardStatus.LIVE,
            returncode=snapshot.returncode,
        )

    def mark_stopped(self, snapshot: PortForwardProcessSnapshot) -> None:
        self.__ensure_finished(snapshot)
        key = PortForwardRowKey.from_snapshot(snapshot)
        row = self.__rows.get(key)

        if row is None:
            raise ValueError(f"Process is not tracked: {key}")

        row.status = PortForwardStatus.STOPPED
        row.returncode = snapshot.returncode

    def mark_died(self, snapshot: PortForwardProcessSnapshot) -> None:
        self.__ensure_finished(snapshot)
        key = PortForwardRowKey.from_snapshot(snapshot)
        row = self.__rows.get(key)

        if row is None:
            raise ValueError(f"Process is not tracked: {key}")

        row.status = PortForwardStatus.DIED
        row.returncode = snapshot.returncode

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
            key = row.key
            table.add_row(
                key.namespace,
                key.service_name,
                f":{key.remote_port}",
                f"localhost:{key.local_port}",
                str(key.pid),
                self.__format_status(row),
            )
        return table

    @staticmethod
    def __format_status(row: _Row) -> str:
        if row.status == PortForwardStatus.LIVE:
            return "[green]● live[/green]"

        if row.status == PortForwardStatus.STOPPED:
            return "[yellow]■ stopped[/yellow]"

        return f"[red]✗ died (exit {row.returncode})[/red]"

    @staticmethod
    def __ensure_finished(snapshot: PortForwardProcessSnapshot) -> None:
        if snapshot.returncode is None:
            raise ValueError("Process is still live")
