from __future__ import annotations

import asyncio
import logging
import signal
from collections.abc import Callable

from kubek.kube import KubeFacade
from rich.live import Live

from portfwd.kube import (
    PortForwardProcess,
    start_port_forward,
)
from portfwd.models import ServicePortForwardPlan
from portfwd.term import make_table
from portfwd.utils import get_port_forward_status_id

logger = logging.getLogger(__name__)


async def watch_processes(
    processes: list[PortForwardProcess],
    statuses: dict[str, str],
    stop_event: asyncio.Event,
    on_exit: Callable[[], None] = lambda: None,
) -> None:
    async def _watch(process: PortForwardProcess) -> None:
        await process.process.wait()
        if not stop_event.is_set():
            statuses[
                get_port_forward_status_id(
                    namespace=process.namespace,
                    service_name=process.service_name,
                    remote_port=process.remote_port,
                )
            ] = f"died (exit {process.process.returncode})"
            on_exit()

    async with asyncio.TaskGroup() as tg:
        for proc in processes:
            tg.create_task(_watch(proc))


async def manage_port_forwards(
    plans: list[ServicePortForwardPlan],
    api: KubeFacade,
) -> None:
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    processes: list[PortForwardProcess] = []
    statuses: dict[str, str] = {}

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
            statuses[
                get_port_forward_status_id(
                    namespace=process.namespace,
                    service_name=process.service_name,
                    remote_port=process.remote_port,
                )
            ] = "live"
    except Exception:
        for proc in processes:
            try:
                proc.process.terminate()
            except ProcessLookupError:
                pass
        raise

    if not processes:
        return

    with Live(
        renderable=make_table(processes, statuses, api.current_config.context),
        refresh_per_second=1,
    ) as live:

        def refresh() -> None:
            live.update(make_table(processes, statuses, api.current_config.context))

        def cleanup() -> None:
            stop_event.set()
            for proc in processes:
                try:
                    proc.process.terminate()
                    statuses[
                        get_port_forward_status_id(
                            namespace=proc.namespace,
                            service_name=proc.service_name,
                            remote_port=proc.remote_port,
                        )
                    ] = "stopped"
                except ProcessLookupError:
                    pass
            refresh()

        loop.add_signal_handler(signal.SIGINT, cleanup)
        loop.add_signal_handler(signal.SIGTERM, cleanup)

        await watch_processes(
            processes=processes,
            statuses=statuses,
            stop_event=stop_event,
            on_exit=refresh,
        )
