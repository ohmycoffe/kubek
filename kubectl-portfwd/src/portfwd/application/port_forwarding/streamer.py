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
        """Start kubectl port-forwards from `plans` and yield lifecycle events until all exit."""
        loop = asyncio.get_running_loop()
        expected_shutdown = asyncio.Event()
        processes: list[PortForwardSession] = []
        event_queue: asyncio.Queue[PortForwardEvent] = asyncio.Queue()
        running = 0

        try:
            for plan in plans:
                process = await self._launcher.launch(plan=plan)
                processes.append(process)
                event_queue.put_nowait(
                    PortForwardEvent(
                        type=PortForwardEventType.STARTED,
                        snapshot=process.snapshot(),
                    )
                )
                running += 1
        except Exception as e:
            self._terminate_all(processes)
            raise PortForwardStartError("failed to start kubectl port-forward") from e

        if not processes:
            return

        def cleanup() -> None:
            expected_shutdown.set()
            self._terminate_all(processes)

        loop.add_signal_handler(signal.SIGINT, cleanup)
        loop.add_signal_handler(signal.SIGTERM, cleanup)

        async def watch(process: PortForwardSession) -> None:
            await process.wait()
            if expected_shutdown.is_set():
                event_type = PortForwardEventType.STOPPED
            else:
                event_type = PortForwardEventType.DIED
            event_queue.put_nowait(
                PortForwardEvent(type=event_type, snapshot=process.snapshot())
            )

        try:
            async with asyncio.TaskGroup() as tg:
                for proc in processes:
                    tg.create_task(watch(proc))

                while running > 0:
                    event = await event_queue.get()
                    if event.exited:
                        running -= 1
                    yield event
        finally:
            loop.remove_signal_handler(signal.SIGINT)
            loop.remove_signal_handler(signal.SIGTERM)

    def _terminate_all(self, processes: list[PortForwardSession]) -> None:
        for proc in processes:
            proc.terminate()
