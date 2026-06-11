from __future__ import annotations

import asyncio
import logging
import signal
from collections.abc import AsyncIterator
from dataclasses import dataclass
from os import PathLike

from kubek.kube.config import ResolvedKubeConfig

from portfwd.application.port_forwarding.events import (
    PortForwardEvent,
    PortForwardEventType,
    PortForwardProcessSnapshot,
)
from portfwd.application.ports import PortForwardRunner
from portfwd.domain.errors import PortForwardStartError
from portfwd.domain.models import ServicePortForwardPlan

logger = logging.getLogger(__name__)


@dataclass
class PortForwardProcess:
    """A running `kubectl port-forward` subprocess and its parameters."""

    process: asyncio.subprocess.Process
    local_port: int
    remote_port: int
    service_name: str
    namespace: str

    def snapshot(self) -> PortForwardProcessSnapshot:
        return PortForwardProcessSnapshot(
            namespace=self.namespace,
            service_name=self.service_name,
            remote_port=self.remote_port,
            local_port=self.local_port,
            pid=self.process.pid,
            returncode=self.process.returncode,
        )


async def start_port_forward(
    namespace: str,
    service: str,
    local_port: int,
    remote_port: int,
    context: str | None,
    kubeconfig: str | PathLike | None = None,
) -> PortForwardProcess:
    """Spawn a `kubectl port-forward` subprocess and return its handle."""
    args: list[str] = []
    if kubeconfig:
        args += ["--kubeconfig", str(kubeconfig)]
    if context:
        args += ["--context", context]
    cmd = [
        "kubectl",
        *args,
        "port-forward",
        f"svc/{service}",
        f"{local_port}:{remote_port}",
        "--namespace",
        namespace,
    ]
    logger.debug(" ".join(cmd))
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=None,
    )

    logger.debug(
        "Started port forward for %s:%d → localhost:%d [PID: %d]",
        service,
        remote_port,
        local_port,
        process.pid,
    )
    return PortForwardProcess(
        process=process,
        local_port=local_port,
        remote_port=remote_port,
        service_name=service,
        namespace=namespace,
    )


class KubectlPortForwardRunner(PortForwardRunner):
    def __init__(self, config: ResolvedKubeConfig) -> None:
        self._config = config

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
        processes: list[PortForwardProcess] = []
        event_queue: asyncio.Queue[PortForwardEvent] = asyncio.Queue()
        running = 0

        try:
            for plan in plans:
                process = await start_port_forward(
                    namespace=plan.target.namespace,
                    service=plan.target.name,
                    local_port=plan.local_port,
                    remote_port=plan.remote_port,
                    context=self._config.context,
                    kubeconfig=self._config.kubeconfig,
                )
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

        async def watch(process: PortForwardProcess) -> None:
            await process.process.wait()
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

    def _terminate_all(self, processes: list[PortForwardProcess]) -> None:
        for proc in processes:
            try:
                proc.process.terminate()
            except ProcessLookupError:
                pass
