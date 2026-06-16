from __future__ import annotations

from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum

from kubek.term.style import Color
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from portfwd.application.port_forwarding.events import (
    OutputLine,
    OutputStream,
    PortForwardEvent,
    PortForwardEventType,
)
from portfwd.application.port_forwarding.snapshot import PortForwardProcessSnapshot

BORDER_STYLE = "bright_black"
_LOG_PANEL_MAX_LINES = 12
_LOG_PANEL_MIN_LINES = 3
_LOG_BUFFER_SIZE = 1000
# Title, borders, column header, caption, log panel chrome, and spacing.
_LAYOUT_OFFSET_LINES = 8
_DEFAULT_TERMINAL_HEIGHT_LINES = 24


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
            border_style=BORDER_STYLE,
            show_lines=False,
        )
        table.add_column("Namespace", style=Color.HIGHLIGHT, no_wrap=True)
        table.add_column("Service", style="bold", no_wrap=True)
        table.add_column("Remote", style=Color.HIGHLIGHT, justify="right")
        table.add_column("Local", style=Color.HIGHLIGHT, justify="right")
        table.add_column("PID", style=Color.MUTED, justify="right")
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
            return f"[{Color.SUCCESS}]● live[/{Color.SUCCESS}]"

        if row.status == _Status.STOPPED:
            return f"[{Color.WARNING}]■ stopped[/{Color.WARNING}]"

        return f"[{Color.ERROR}]✗ died (exit {row.returncode})[/{Color.ERROR}]"

    @staticmethod
    def __ensure_finished(snapshot: PortForwardProcessSnapshot) -> None:
        if snapshot.returncode is None:
            raise ValueError("Process is still live")

    @property
    def rows_number(self) -> int:
        return len(self.__rows)


class _LogPanel:
    """Owns a bounded buffer of recent subprocess output, rendered as a `Panel`."""

    def __init__(self) -> None:
        self.__log_buffer: deque[Text] = deque(maxlen=_LOG_BUFFER_SIZE)

    def append(
        self,
        snapshot: PortForwardProcessSnapshot,
        output: OutputLine,
    ) -> None:
        source = f"{snapshot.service_name}:{snapshot.local_port}"
        body_style = (
            Color.ERROR if output.stream == OutputStream.STDERR else Color.MUTED
        )

        log_line = Text(no_wrap=False)
        log_line.append(f"{source} ", style=Color.HIGHLIGHT)
        log_line.append(output.text, style=body_style)
        self.__log_buffer.append(log_line)

    def render(self, height: int, width: int | None = None) -> Panel:
        newest_log_entries = list(self.__log_buffer)[-height:]
        if not newest_log_entries:
            newest_log_entries = [Text("Waiting for output…", style=Color.MUTED)]

        # Pad with blank lines so the panel height stays fixed from the start.
        blank_padding_lines = height - len(newest_log_entries)
        padded_log_lines = newest_log_entries + [
            Text("") for _ in range(max(blank_padding_lines, 0))
        ]

        return Panel(
            Text("\n").join(padded_log_lines),
            title="[bold]Logs[/bold]",
            border_style=BORDER_STYLE,
            width=width,
        )


class PortForwardLiveDisplay:
    """Applies port-forward lifecycle events to a Rich live status table."""

    def __init__(self, context: str | None, console: Console) -> None:
        self._console = console
        self._table = _PortForwardStatusTable(context=context)
        self._logs = _LogPanel()
        self._live: Live | None = None

    @contextmanager
    def live(self) -> Iterator[None]:
        with Live(
            renderable=Text("Starting port forwards…", style="dim"),
            vertical_overflow="crop",
            console=self._console,
        ) as live:
            self._live = live
            try:
                yield
            finally:
                self._live = None

    def apply(self, event: PortForwardEvent) -> None:
        """Update the status table and logs from a port-forward event."""
        if event.type == PortForwardEventType.STARTED:
            self._table.track(event.snapshot)
        elif event.type == PortForwardEventType.STOPPED:
            self._table.mark_stopped(event.snapshot)
        elif event.type == PortForwardEventType.DIED:
            self._table.mark_died(event.snapshot)
        elif event.type == PortForwardEventType.OUTPUT and event.output is not None:
            self._logs.append(event.snapshot, event.output)
        self._refresh()

    def _refresh(self) -> None:
        if self._live is not None:
            self._live.update(self._render())

    def _calculate_log_panel_height(self, rows_number: int) -> int:
        terminal_height = self._console.size.height or _DEFAULT_TERMINAL_HEIGHT_LINES
        log_panel_height = terminal_height - rows_number - _LAYOUT_OFFSET_LINES
        return max(
            _LOG_PANEL_MIN_LINES,
            min(_LOG_PANEL_MAX_LINES, log_panel_height),
        )

    def _render(self) -> Group:
        status_table = self._table.render()
        logs_panel = self._logs.render(
            height=self._calculate_log_panel_height(self._table.rows_number),
            width=self._console.measure(status_table).maximum,
        )
        return Group(status_table, logs_panel)
