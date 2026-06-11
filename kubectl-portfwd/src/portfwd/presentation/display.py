from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum

from rich.live import Live
from rich.table import Table
from rich.text import Text

from portfwd.application.port_forwarding.events import (
    PortForwardEvent,
    PortForwardEventType,
    PortForwardProcessSnapshot,
)


class _Status(StrEnum):
    LIVE = "live"
    STOPPED = "stopped"
    DIED = "died"


@dataclass(frozen=True)
class _RowKey:
    namespace: str
    service_name: str
    remote_port: int
    local_port: int
    pid: int

    @classmethod
    def from_snapshot(
        cls,
        snapshot: PortForwardProcessSnapshot,
    ) -> _RowKey:
        return cls(
            namespace=snapshot.namespace,
            service_name=snapshot.service_name,
            remote_port=snapshot.remote_port,
            local_port=snapshot.local_port,
            pid=snapshot.pid,
        )


@dataclass
class _RowState:
    status: _Status
    returncode: int | None = None


class _PortForwardStatusTable:
    """Owns per-process status state and renders it as a Rich `Table`.

    Encapsulates the row-key scheme so callers never deal with strings.
    """

    def __init__(self, context: str | None = None) -> None:
        self.__context = context
        self.__rows: dict[_RowKey, _RowState] = {}

    def track(self, snapshot: PortForwardProcessSnapshot) -> None:
        key = _RowKey.from_snapshot(snapshot)

        self.__rows[key] = _RowState(
            status=_Status.LIVE,
            returncode=snapshot.returncode,
        )

    def mark_stopped(self, snapshot: PortForwardProcessSnapshot) -> None:
        self.__ensure_finished(snapshot)
        key = _RowKey.from_snapshot(snapshot)
        row = self.__rows.get(key)

        if row is None:
            raise ValueError(f"Process is not tracked: {key}")

        row.status = _Status.STOPPED
        row.returncode = snapshot.returncode

    def mark_died(self, snapshot: PortForwardProcessSnapshot) -> None:
        self.__ensure_finished(snapshot)
        key = _RowKey.from_snapshot(snapshot)
        row = self.__rows.get(key)

        if row is None:
            raise ValueError(f"Process is not tracked: {key}")

        row.status = _Status.DIED
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
        for row_key, row_state in self.__rows.items():
            key = row_key
            table.add_row(
                key.namespace,
                key.service_name,
                f":{key.remote_port}",
                f"localhost:{key.local_port}",
                str(key.pid),
                self.__format_status(row_state),
            )
        return table

    @staticmethod
    def __format_status(row: _RowState) -> str:
        if row.status == _Status.LIVE:
            return "[green]● live[/green]"

        if row.status == _Status.STOPPED:
            return "[yellow]■ stopped[/yellow]"

        return f"[red]✗ died (exit {row.returncode})[/red]"

    @staticmethod
    def __ensure_finished(snapshot: PortForwardProcessSnapshot) -> None:
        if snapshot.returncode is None:
            raise ValueError("Process is still live")


class PortForwardLiveDisplay:
    """Applies port-forward lifecycle events to a Rich live status table."""

    def __init__(self, context: str | None) -> None:
        self._table = _PortForwardStatusTable(context=context)
        self._live: Live | None = None

    @contextmanager
    def live(self) -> Iterator[None]:
        with Live(
            renderable=Text("Starting port forwards…", style="dim"),
            refresh_per_second=1,
        ) as live:
            self._live = live
            try:
                yield
            finally:
                self._live = None

    def apply(self, event: PortForwardEvent) -> None:
        """Update the status table from a port-forward lifecycle event."""
        if event.type == PortForwardEventType.STARTED:
            self._table.track(event.snapshot)
        elif event.type == PortForwardEventType.STOPPED:
            self._table.mark_stopped(event.snapshot)
        elif event.type == PortForwardEventType.DIED:
            self._table.mark_died(event.snapshot)
        self._refresh()

    def _refresh(self) -> None:
        if self._live is not None:
            self._live.update(self._table.render())
