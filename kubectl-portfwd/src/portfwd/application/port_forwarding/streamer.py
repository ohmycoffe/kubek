from __future__ import annotations

import asyncio
import signal
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass

from portfwd.application.port_forwarding.events import (
    PortForwardDied,
    PortForwardEvent,
    PortForwardLaunchAbandoned,
    PortForwardLaunchFailed,
    PortForwardLocalPortBusy,
    PortForwardOutput,
    PortForwardReconnecting,
    PortForwardShutdownWhileWaiting,
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
    """Exponential backoff delays in seconds for retries and port-busy polls.

    Launch retries share one delay sequence for a forward's whole lifetime, so a
    rapidly crash-looping forward keeps backing off instead of resetting to
    ``min_s`` on every restart. Port-busy polls use a fresh sequence on each
    wait. ``max_retries`` applies to launch retries only.
    """

    min_s: float = 0.5
    max_s: float = 30.0
    max_retries: int = 10

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


@dataclass
class _RetryCounter:
    """Counts failed launch attempts; stops once ``attempt`` reaches ``max_retries``."""

    max_retries: int
    attempt: int = 0

    def record(self) -> None:
        self.attempt += 1

    def exceeded(self) -> bool:
        return self.attempt >= self.max_retries


class PortForwardEventStreamer(PortForwardEventStream):
    def __init__(
        self,
        launcher: PortForwardLauncher,
        *,
        is_local_port_free: Callable[[int], bool],
        backoff: Backoff | None = None,
    ) -> None:
        self._launcher = launcher
        self._is_local_port_free = is_local_port_free
        self._backoff = backoff or Backoff()

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
                    if isinstance(event, _SupervisorExited):
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
        """Keep one port-forward alive, restarting it on the same local port until shutdown.

        A single backoff sequence is shared across restarts so a crash-looping
        forward keeps backing off instead of resetting to ``min_s`` each time.
        Restarts stop once ``Backoff.max_retries`` is exhausted.
        """
        retry_delays = self._backoff.retry_delays()
        retry_counter = _RetryCounter(max_retries=self._backoff.max_retries)
        try:
            while not expected_shutdown.is_set():
                process = await self._launch_with_retry(
                    plan=plan,
                    events=events,
                    expected_shutdown=expected_shutdown,
                    retry_delays=retry_delays,
                    retry_counter=retry_counter,
                )
                if process is None:
                    if expected_shutdown.is_set():
                        events.put_nowait(
                            PortForwardShutdownWhileWaiting(
                                kind=plan.target.kind,
                                namespace=plan.target.namespace,
                                name=plan.target.name,
                                remote_port=plan.remote_port,
                                local_port=plan.local_port,
                            )
                        )
                    elif retry_counter.exceeded():
                        self._emit_launch_abandoned(
                            plan=plan,
                            events=events,
                            retry_counter=retry_counter,
                        )
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
                retry_counter.record()
                if retry_counter.exceeded():
                    self._emit_launch_abandoned(
                        plan=plan,
                        events=events,
                        retry_counter=retry_counter,
                    )
                    return
        finally:
            events.put_nowait(_SUPERVISOR_EXITED)

    async def _launch_with_retry(
        self,
        *,
        plan: PortForwardPlan,
        events: asyncio.Queue[_Queued],
        expected_shutdown: asyncio.Event,
        retry_delays: Iterator[float],
        retry_counter: _RetryCounter,
    ) -> PortForwardSession | None:
        """Wait for the local port, then launch; retry with backoff until shutdown.

        Advances the shared ``retry_delays`` sequence so delays keep growing
        across restarts. Returns the running session, or ``None`` if shutdown
        was requested first or ``Backoff.max_retries`` is exhausted. Each failed
        attempt emits a ``LAUNCH_FAILED`` event so the UI can show it.
        """
        while not expected_shutdown.is_set():
            if retry_counter.attempt > 0:
                events.put_nowait(
                    PortForwardReconnecting(
                        kind=plan.target.kind,
                        namespace=plan.target.namespace,
                        name=plan.target.name,
                        remote_port=plan.remote_port,
                        local_port=plan.local_port,
                        attempt=retry_counter.attempt + 1,
                    )
                )

            await self._sleep_or_shutdown(
                next(retry_delays),
                expected_shutdown,
            )

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
                retry_counter.record()
                events.put_nowait(
                    PortForwardLaunchFailed(
                        kind=plan.target.kind,
                        namespace=plan.target.namespace,
                        name=plan.target.name,
                        remote_port=plan.remote_port,
                        local_port=plan.local_port,
                        reason=str(exc),
                        attempt=retry_counter.attempt,
                    )
                )
                if retry_counter.exceeded():
                    return None

        return None

    async def _wait_for_local_port(
        self,
        *,
        plan: PortForwardPlan,
        events: asyncio.Queue[_Queued],
        expected_shutdown: asyncio.Event,
    ) -> bool:
        """Wait until the planned local port can be bound again before relaunching.

        Uses a local poll counter and a fresh backoff sequence (both reset on
        each call) and emits a ``PortForwardLocalPortBusy`` event on each poll
        while the port stays busy. Polls indefinitely until the port frees or
        shutdown.
        """
        poll_delays = self._backoff.retry_delays()
        poll = 0

        while not expected_shutdown.is_set():
            if self._is_local_port_free(plan.local_port):
                return True

            poll += 1
            events.put_nowait(
                PortForwardLocalPortBusy(
                    kind=plan.target.kind,
                    namespace=plan.target.namespace,
                    name=plan.target.name,
                    remote_port=plan.remote_port,
                    local_port=plan.local_port,
                    poll=poll,
                )
            )

            await self._sleep_or_shutdown(
                next(poll_delays),
                expected_shutdown,
            )

        return False

    async def _sleep_or_shutdown(
        self,
        delay: float,
        expected_shutdown: asyncio.Event,
    ) -> None:
        """Sleep for ``delay`` seconds unless shutdown is requested first."""
        if expected_shutdown.is_set():
            return

        try:
            await asyncio.wait_for(expected_shutdown.wait(), timeout=delay)
        except TimeoutError:
            return

    async def emit_output(
        self,
        process: PortForwardSession,
        events: asyncio.Queue[_Queued],
    ) -> None:
        async for output in process.stream_output():
            events.put_nowait(
                PortForwardOutput(snapshot=process.snapshot(), output=output)
            )

    def _emit_launch_abandoned(
        self,
        *,
        plan: PortForwardPlan,
        events: asyncio.Queue[_Queued],
        retry_counter: _RetryCounter,
    ) -> None:
        events.put_nowait(
            PortForwardLaunchAbandoned(
                kind=plan.target.kind,
                namespace=plan.target.namespace,
                name=plan.target.name,
                remote_port=plan.remote_port,
                local_port=plan.local_port,
                max_retries=retry_counter.max_retries,
            )
        )

    def _terminate_all(self, processes: list[PortForwardSession]) -> None:
        for proc in processes:
            proc.terminate()
