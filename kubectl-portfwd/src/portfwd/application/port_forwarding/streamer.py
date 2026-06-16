from __future__ import annotations

import asyncio
import logging
import signal
from collections.abc import AsyncIterator

from portfwd.application.port_forwarding.events import (
    PortForwardEvent,
    PortForwardEventType,
)
from portfwd.application.ports import (
    PortForwardEventStream,
    PortForwardLauncher,
    PortForwardSession,
)
from portfwd.domain.errors import PortForwardStartError
from portfwd.domain.models import ServicePortForwardPlan

logger = logging.getLogger(__name__)


class PortForwardEventStreamer(PortForwardEventStream):
    def __init__(self, launcher: PortForwardLauncher) -> None:
        self._launcher = launcher

    def stream(
        self, plans: list[ServicePortForwardPlan]
    ) -> AsyncIterator[PortForwardEvent]:
        return self.stream_port_forwards(plans=plans)

    async def stream_port_forwards(
        self,
        plans: list[ServicePortForwardPlan],
    ) -> AsyncIterator[PortForwardEvent]:
        """Start kubectl port-forwards from `plans` and yield events until all exit."""
        loop = asyncio.get_running_loop()
        expected_shutdown = asyncio.Event()
        processes: list[PortForwardSession] = []

        def on_signal() -> None:
            expected_shutdown.set()
            self._terminate_all(processes)

        loop.add_signal_handler(signal.SIGINT, on_signal)
        loop.add_signal_handler(signal.SIGTERM, on_signal)

        try:
            try:
                for plan in plans:
                    process = await self._launcher.launch(plan=plan)
                    processes.append(process)
                    yield PortForwardEvent(
                        type=PortForwardEventType.STARTED,
                        snapshot=process.snapshot(),
                    )
            except Exception as e:
                self._terminate_all(processes)
                raise PortForwardStartError(
                    "failed to start kubectl port-forward"
                ) from e

            if not processes:
                return

            events: asyncio.Queue[PortForwardEvent] = asyncio.Queue()

            async with asyncio.TaskGroup() as tg:
                for process in processes:
                    tg.create_task(
                        self.monitor_session(process, events, expected_shutdown)
                    )

                sessions_left = len(processes)
                while sessions_left > 0:
                    event = await events.get()
                    if event.is_control:
                        sessions_left -= 1
                        continue
                    yield event
        finally:
            loop.remove_signal_handler(signal.SIGINT)
            loop.remove_signal_handler(signal.SIGTERM)

    async def monitor_session(
        self,
        process: PortForwardSession,
        events: asyncio.Queue[PortForwardEvent],
        expected_shutdown: asyncio.Event,
    ) -> None:
        """Emit subprocess output while the process runs, then emit its exit event."""
        emit = asyncio.create_task(self.emit_output(process, events))
        try:
            await process.wait()
            await emit
            if expected_shutdown.is_set():
                event_type = PortForwardEventType.STOPPED
            else:
                event_type = PortForwardEventType.DIED
            events.put_nowait(
                PortForwardEvent(type=event_type, snapshot=process.snapshot())
            )
        finally:
            if not emit.done():
                emit.cancel()
            events.put_nowait(
                PortForwardEvent(
                    type=PortForwardEventType.SESSION_DONE,
                    snapshot=process.snapshot(),
                )
            )

    async def emit_output(
        self,
        process: PortForwardSession,
        events: asyncio.Queue[PortForwardEvent],
    ) -> None:
        async for output in process.stream_output():
            events.put_nowait(
                PortForwardEvent(
                    type=PortForwardEventType.OUTPUT,
                    snapshot=process.snapshot(),
                    output=output,
                )
            )

    def _terminate_all(self, processes: list[PortForwardSession]) -> None:
        for proc in processes:
            proc.terminate()
