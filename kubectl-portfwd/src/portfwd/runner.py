from __future__ import annotations

import asyncio
import logging
import signal
from collections.abc import Callable

from kubek.kube import KubeFacade
from rich.live import Live

from portfwd.display import LiveStatusTable
from portfwd.domain.errors import PortForwardStartError
from portfwd.domain.models import ServicePortForwardPlan
from portfwd.kubectl import PortForwardProcess, start_port_forward

logger = logging.getLogger(__name__)


async def watch_processes(
    processes: list[PortForwardProcess],
    table: LiveStatusTable,
    expected_shutdown: asyncio.Event,
    on_change: Callable[[], None] = lambda: None,
) -> None:
    """Await every kubectl port-forward subprocess and update statuses on exit."""

    async def _watch(process: PortForwardProcess) -> None:
        await process.process.wait()
        if expected_shutdown.is_set():
            table.mark_stopped(process)
        else:
            table.mark_died(process)
        on_change()

    async with asyncio.TaskGroup() as tg:
        for proc in processes:
            tg.create_task(_watch(proc))


async def manage_port_forwards(
    plans: list[ServicePortForwardPlan],
    api: KubeFacade,
) -> None:
    """Start, watch, and tear down all kubectl port-forwards from `plans`."""
    loop = asyncio.get_running_loop()
    expected_shutdown = asyncio.Event()
    table = LiveStatusTable(context=api.current_config.context)
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
            table.track(process)
    except Exception as e:
        _terminate_all(processes)
        raise PortForwardStartError("failed to start kubectl port-forward") from e

    if not processes:
        return

    with Live(renderable=table.render(), refresh_per_second=1) as live:

        def refresh() -> None:
            live.update(table.render())

        def cleanup() -> None:
            expected_shutdown.set()
            for proc in processes:
                try:
                    proc.process.terminate()
                except ProcessLookupError:
                    pass
            refresh()

        loop.add_signal_handler(signal.SIGINT, cleanup)
        loop.add_signal_handler(signal.SIGTERM, cleanup)

        await watch_processes(
            processes=processes,
            table=table,
            expected_shutdown=expected_shutdown,
            on_change=refresh,
        )


def _terminate_all(processes: list[PortForwardProcess]) -> None:
    for proc in processes:
        try:
            proc.process.terminate()
        except ProcessLookupError:
            pass
