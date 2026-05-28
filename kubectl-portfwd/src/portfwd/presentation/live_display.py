from typing import Self

from rich.live import Live

from portfwd.application.port_forwarding.events import (
    PortForwardEvents,
    PortForwardProcessSnapshot,
)
from portfwd.presentation.display import LiveStatusTable


class PortForwardLiveDisplay:
    """Connects runner callbacks to Rich LiveStatusTable."""

    def __init__(self, context: str | None) -> None:
        self._table = LiveStatusTable(context=context)
        self._live: Live | None = None

    def events(self) -> PortForwardEvents:
        return PortForwardEvents(
            on_started=self.started,
            on_stopped=self.stopped,
            on_died=self.died,
        )

    def __enter__(self) -> Self:
        self._live = Live(
            renderable=self._table.render(),
            refresh_per_second=1,
        )
        self._live.__enter__()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._live is not None:
            self._live.__exit__(exc_type, exc, traceback)

    def started(self, snapshot: PortForwardProcessSnapshot) -> None:
        self._table.track(snapshot)
        self._refresh()

    def stopped(self, snapshot: PortForwardProcessSnapshot) -> None:
        self._table.mark_stopped(snapshot)
        self._refresh()

    def died(self, snapshot: PortForwardProcessSnapshot) -> None:
        self._table.mark_died(snapshot)
        self._refresh()

    def _refresh(self) -> None:
        if self._live is not None:
            self._live.update(self._table.render())
