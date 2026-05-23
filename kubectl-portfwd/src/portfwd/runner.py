from __future__ import annotations

import asyncio
import logging
import signal
from collections.abc import Callable

from kubek.kube import KubeFacade
from rich.live import Live

from portfwd.display import LiveStatusTable
from portfwd.errors import PortForwardStartError
from portfwd.kubectl import PortForwardProcess, start_port_forward
from portfwd.models import ServicePortForwardPlan

logger = logging.getLogger(__name__)


async def watch_processes(
    processes: list[PortForwardProcess],
    table: LiveStatusTable,
    stop_event: asyncio.Event,
    on_change: Callable[[], None] = lambda: None,
) -> None:
    """Await every kubectl port-forward subprocess and update statuses on exit."""

    async def _watch(process: PortForwardProcess) -> None:
        await process.process.wait()
        if not stop_event.is_set():
            table.mark_died(process, process.process.returncode)
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
    stop_event = asyncio.Event()
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
            stop_event.set()
            for proc in processes:
                try:
                    proc.process.terminate()
                    table.mark_stopped(proc)
                except ProcessLookupError:
                    pass
            refresh()

        loop.add_signal_handler(signal.SIGINT, cleanup)
        loop.add_signal_handler(signal.SIGTERM, cleanup)

        await watch_processes(
            processes=processes,
            table=table,
            stop_event=stop_event,
            on_change=refresh,
        )


def _terminate_all(processes: list[PortForwardProcess]) -> None:
    for proc in processes:
        try:
            proc.process.terminate()
        except ProcessLookupError:
            pass
