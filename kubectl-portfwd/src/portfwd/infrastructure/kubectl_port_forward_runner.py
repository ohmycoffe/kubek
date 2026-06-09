from __future__ import annotations

import asyncio
import logging
import signal
from dataclasses import dataclass
from os import PathLike

from kubek.kube import KubeFacade

from portfwd.application.port_forwarding.events import (
    PortForwardEvents,
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


async def watch_processes(
    processes: list[PortForwardProcess],
    expected_shutdown: asyncio.Event,
    events: PortForwardEvents,
) -> None:
    """Await every kubectl port-forward subprocess and update statuses on exit."""

    async def watch(process: PortForwardProcess) -> None:
        await process.process.wait()
        if expected_shutdown.is_set():
            events.on_stopped(process.snapshot())
        else:
            events.on_died(process.snapshot())

    async with asyncio.TaskGroup() as tg:
        for proc in processes:
            tg.create_task(watch(proc))


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
    def __init__(
        self,
        api: KubeFacade,
        events: PortForwardEvents | None = None,
    ) -> None:
        self._api = api
        self._events = events or PortForwardEvents()

    async def run(self, plans: list[ServicePortForwardPlan]) -> None:
        await manage_port_forwards(
            plans=plans,
            api=self._api,
            events=self._events,
        )


async def manage_port_forwards(
    plans: list[ServicePortForwardPlan],
    api: KubeFacade,
    events: PortForwardEvents,
) -> None:
    """Start, watch, and tear down all kubectl port-forwards from `plans`."""
    loop = asyncio.get_running_loop()
    expected_shutdown = asyncio.Event()
    processes: list[PortForwardProcess] = []

    try:
        for plan in plans:
            process = await start_port_forward(
                namespace=plan.target.namespace,
                service=plan.target.name,
                local_port=plan.local_port,
                remote_port=plan.remote_port,
                context=api.current_config.context,
                kubeconfig=api.current_config.kubeconfig,
            )
            processes.append(process)
            events.on_started(process.snapshot())
    except Exception as e:
        _terminate_all(processes)
        raise PortForwardStartError("failed to start kubectl port-forward") from e

    if not processes:
        return

    def cleanup() -> None:
        expected_shutdown.set()
        _terminate_all(processes)

    loop.add_signal_handler(signal.SIGINT, cleanup)
    loop.add_signal_handler(signal.SIGTERM, cleanup)

    await watch_processes(
        processes=processes,
        expected_shutdown=expected_shutdown,
        events=events,
    )


def _terminate_all(processes: list[PortForwardProcess]) -> None:
    for proc in processes:
        try:
            proc.process.terminate()
        except ProcessLookupError:
            pass
