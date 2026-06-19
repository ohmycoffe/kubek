from __future__ import annotations

import asyncio
import signal
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from dataclasses import dataclass

from portfwd.application.port_forwarding.events import (
    PortForwardDied,
    PortForwardEvent,
    PortForwardLaunchFailed,
    PortForwardOutput,
    PortForwardReconnecting,
    PortForwardStarted,
    PortForwardStopped,
)
from portfwd.application.ports import (
    PortForwardEventStream,
    PortForwardLauncher,
    PortForwardSession,
)
from portfwd.domain.models import PortForwardPlan


@dataclass(frozen=True)
class Backoff:
    """Retry sleeps for launch failures and port-busy polls (exponential backoff in seconds)."""

    min_s: float = 0.5
    max_s: float = 30.0

    def retry_delays(self) -> Iterator[float]:
        """Yield sleep durations (in seconds)"""
        delay_s = self.min_s
        while True:
            yield delay_s
            delay_s = min(delay_s * 2, self.max_s)


class _SupervisorExited:
    """Internal sentinel: one supervisor task has finished for good.

    Put on the shared queue so the consumer can count down active supervisors
    (the "poison pill" pattern); never yielded to the presentation layer.
    """

    __slots__ = ()


_SUPERVISOR_EXITED = _SupervisorExited()

_Queued = PortForwardEvent | _SupervisorExited


class PortForwardEventStreamer(PortForwardEventStream):
    def __init__(
        self,
        launcher: PortForwardLauncher,
        *,
        is_local_port_free: Callable[[int], bool],
        backoff: Backoff | None = None,
        sleep_for: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._launcher = launcher
        self._is_local_port_free = is_local_port_free
        self._backoff = backoff or Backoff()
        self._sleep_for = sleep_for

    def stream(self, plans: list[PortForwardPlan]) -> AsyncIterator[PortForwardEvent]:
        return self._stream_port_forwards(plans=plans)

    async def _stream_port_forwards(
        self,
        plans: list[PortForwardPlan],
    ) -> AsyncIterator[PortForwardEvent]:
        """Start kubectl port-forwards from `plans` and yield events until shutdown."""
        if not plans:
            return

        loop = asyncio.get_running_loop()
        expected_shutdown = asyncio.Event()
        active_processes: list[PortForwardSession] = []

        def on_signal() -> None:
            expected_shutdown.set()
            self._terminate_all(active_processes)

        loop.add_signal_handler(signal.SIGINT, on_signal)
        loop.add_signal_handler(signal.SIGTERM, on_signal)

        try:
            events: asyncio.Queue[_Queued] = asyncio.Queue()

            async with asyncio.TaskGroup() as tg:
                for plan in plans:
                    tg.create_task(
                        self._supervise_port_forward(
                            plan=plan,
                            events=events,
                            expected_shutdown=expected_shutdown,
                            active_processes=active_processes,
                        )
                    )

                plans_remaining = len(plans)
                while plans_remaining > 0:
                    event = await events.get()
                    if event is _SUPERVISOR_EXITED:
                        plans_remaining -= 1
                        continue
                    yield event
        finally:
            loop.remove_signal_handler(signal.SIGINT)
            loop.remove_signal_handler(signal.SIGTERM)

    async def _supervise_port_forward(
        self,
        *,
        plan: PortForwardPlan,
        events: asyncio.Queue[_Queued],
        expected_shutdown: asyncio.Event,
        active_processes: list[PortForwardSession],
    ) -> None:
        """Keep one port-forward alive, restarting it on the same local port until shutdown."""
        try:
            while not expected_shutdown.is_set():
                process = await self._launch_with_retry(
                    plan=plan,
                    events=events,
                    expected_shutdown=expected_shutdown,
                )
                if process is None:
                    return

                active_processes.append(process)
                events.put_nowait(PortForwardStarted(snapshot=process.snapshot()))

                emit = asyncio.create_task(self.emit_output(process, events))
                try:
                    await process.wait()
                    await emit
                finally:
                    if not emit.done():
                        emit.cancel()
                    if process in active_processes:
                        active_processes.remove(process)

                if expected_shutdown.is_set():
                    events.put_nowait(PortForwardStopped(snapshot=process.snapshot()))
                    return

                events.put_nowait(PortForwardDied(snapshot=process.snapshot()))
        finally:
            events.put_nowait(_SUPERVISOR_EXITED)

    async def _launch_with_retry(
        self,
        *,
        plan: PortForwardPlan,
        events: asyncio.Queue[_Queued],
        expected_shutdown: asyncio.Event,
    ) -> PortForwardSession | None:
        """Wait for the local port, then launch; retry with backoff until shutdown.

        Returns the running session, or ``None`` if shutdown was requested first.
        Each failed attempt emits a ``LAUNCH_FAILED`` event so the UI can show it.
        """
        backoff = self._backoff.retry_delays()

        while not expected_shutdown.is_set():
            # Minimal delay before each launch attempt (including the first)
            await self._sleep_for(next(backoff))

            if not await self._wait_for_local_port(
                plan=plan,
                events=events,
                expected_shutdown=expected_shutdown,
            ):
                return None

            try:
                return await self._launcher.launch(plan=plan)
            except Exception as exc:
                if expected_shutdown.is_set():
                    return None
                events.put_nowait(
                    PortForwardLaunchFailed(
                        kind=plan.target.kind,
                        namespace=plan.target.namespace,
                        name=plan.target.name,
                        remote_port=plan.remote_port,
                        local_port=plan.local_port,
                        reason=str(exc),
                    )
                )

        return None

    async def _wait_for_local_port(
        self,
        *,
        plan: PortForwardPlan,
        events: asyncio.Queue[_Queued],
        expected_shutdown: asyncio.Event,
    ) -> bool:
        """Wait until the planned local port can be bound again before relaunching.

        Emits a ``PortForwardReconnecting`` event on each poll while the port
        stays busy so the UI logs every reconnect attempt.
        """
        backoff = self._backoff.retry_delays()

        while not expected_shutdown.is_set():
            if self._is_local_port_free(plan.local_port):
                return True

            events.put_nowait(
                PortForwardReconnecting(
                    kind=plan.target.kind,
                    namespace=plan.target.namespace,
                    name=plan.target.name,
                    remote_port=plan.remote_port,
                    local_port=plan.local_port,
                )
            )

            await self._sleep_for(next(backoff))

        return False

    async def emit_output(
        self,
        process: PortForwardSession,
        events: asyncio.Queue[_Queued],
    ) -> None:
        async for output in process.stream_output():
            events.put_nowait(
                PortForwardOutput(snapshot=process.snapshot(), output=output)
            )

    def _terminate_all(self, processes: list[PortForwardSession]) -> None:
        for proc in processes:
            proc.terminate()
