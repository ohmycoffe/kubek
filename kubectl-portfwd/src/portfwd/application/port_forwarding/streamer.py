from __future__ import annotations

import asyncio
import signal
from collections.abc import AsyncIterator, Awaitable, Callable
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
from portfwd.domain.models import ServicePortForwardPlan


@dataclass(frozen=True)
class RestartDelays:
    """Delays governing how a dead port-forward is restarted."""

    min_s: float = 5.0
    poll_s: float = 1.0
    max_s: float = 30.0


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
        restart_delays: RestartDelays | None = None,
        sleep_for: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._launcher = launcher
        self._is_local_port_free = is_local_port_free
        self._restart_delays = restart_delays or RestartDelays()
        self._sleep_for = sleep_for

    def stream(
        self, plans: list[ServicePortForwardPlan]
    ) -> AsyncIterator[PortForwardEvent]:
        return self._stream_port_forwards(plans=plans)

    async def _stream_port_forwards(
        self,
        plans: list[ServicePortForwardPlan],
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
        plan: ServicePortForwardPlan,
        events: asyncio.Queue[_Queued],
        expected_shutdown: asyncio.Event,
        active_processes: list[PortForwardSession],
    ) -> None:
        """Keep one port-forward alive, restarting it on the same local port until shutdown."""
        after_death = False

        try:
            while not expected_shutdown.is_set():
                if after_death:
                    if not await self._wait_before_reconnect(expected_shutdown):
                        return
                    after_death = False

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
                after_death = True
        finally:
            events.put_nowait(_SUPERVISOR_EXITED)

    async def _launch_with_retry(
        self,
        *,
        plan: ServicePortForwardPlan,
        events: asyncio.Queue[_Queued],
        expected_shutdown: asyncio.Event,
    ) -> PortForwardSession | None:
        """Wait for the local port, then launch; retry with backoff until shutdown.

        Returns the running session, or ``None`` if shutdown was requested first.
        Each failed attempt emits a ``LAUNCH_FAILED`` event so the UI can show it.
        """
        retry_delay_s = self._restart_delays.poll_s

        while not expected_shutdown.is_set():
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
                        namespace=plan.target.namespace,
                        service_name=plan.target.name,
                        remote_port=plan.remote_port,
                        local_port=plan.local_port,
                        reason=str(exc),
                    )
                )
                await self._sleep_for(retry_delay_s)
                retry_delay_s = min(retry_delay_s * 2, self._restart_delays.max_s)

        return None

    async def _wait_for_local_port(
        self,
        *,
        plan: ServicePortForwardPlan,
        events: asyncio.Queue[_Queued],
        expected_shutdown: asyncio.Event,
    ) -> bool:
        """Wait until the planned local port can be bound again before relaunching.

        Emits a ``PortForwardReconnecting`` event on each poll while the port
        stays busy so the UI logs every reconnect attempt.
        """
        while not expected_shutdown.is_set():
            if self._is_local_port_free(plan.local_port):
                return True

            events.put_nowait(
                PortForwardReconnecting(
                    namespace=plan.target.namespace,
                    service_name=plan.target.name,
                    remote_port=plan.remote_port,
                    local_port=plan.local_port,
                )
            )

            await self._sleep_for(self._restart_delays.poll_s)

        return False

    async def _wait_before_reconnect(self, expected_shutdown: asyncio.Event) -> bool:
        """Wait at least the minimum delay before reconnecting.

        Returns ``True`` if the delay elapsed and a reconnect should proceed, or
        ``False`` if shutdown was requested during the wait.
        """
        try:
            await asyncio.wait_for(
                expected_shutdown.wait(),
                timeout=self._restart_delays.min_s,
            )
            return False
        except TimeoutError:
            return True

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
