import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import typer
from portfwd.config import ServiceConfig
from portfwd.kube import KubernetesService, PortForwardProcess
from portfwd.runner import ensure_local_ports, watch_processes
from portfwd.ui.display import make_table


def _make_service(name: str, port: int, namespace: str = "ns") -> KubernetesService:
    return KubernetesService(name=name, port=port, protocol="TCP", namespace=namespace)


def _make_process(
    service_name: str, remote_port: int, local_port: int, returncode: int = 0
) -> PortForwardProcess:
    proc = MagicMock()
    proc.pid = 1234
    proc.returncode = returncode
    proc.wait = AsyncMock()
    return PortForwardProcess(
        process=proc,
        service_name=service_name,
        remote_port=remote_port,
        local_port=local_port,
        namespace="ns",
    )


_SVC_CONFIG = ServiceConfig(name="svc", namespace="ns", remote_port=80, local_port=9000)


def test_resolve_local_ports_uses_preferred_port():
    """Uses the configured local port when the preferred port is free."""
    services = [_make_service("svc", 80)]

    with patch("portfwd.runner.is_port_free", return_value=True):
        result = ensure_local_ports(services, [_SVC_CONFIG])

    assert result == [(services[0], 9000)]


def test_resolve_local_ports_fails_when_preferred_unavailable():
    """Hard-fails when the configured local port is already in use."""
    services = [_make_service("svc", 80)]

    with (
        patch("portfwd.runner.is_port_free", return_value=False),
        patch("portfwd.runner.console"),
        pytest.raises(typer.Exit) as exc_info,
    ):
        ensure_local_ports(services, [_SVC_CONFIG])

    assert exc_info.value.exit_code == 1


def test_resolve_local_ports_no_config_match():
    """Assigns a random free port when no config entry matches the service."""
    services = [_make_service("svc", 80)]

    with patch("portfwd.runner.find_free_port", return_value=50000):
        result = ensure_local_ports(services, [])

    assert result == [(services[0], 50000)]


def test_resolve_local_ports_ignores_config_from_other_namespace():
    """Does not use config entries whose namespace does not match."""
    services = [_make_service("svc", 80, namespace="ns")]
    other_ns = ServiceConfig(
        name="svc", namespace="other-ns", remote_port=80, local_port=9000
    )

    with patch("portfwd.runner.find_free_port", return_value=50000):
        result = ensure_local_ports(services, [other_ns])

    assert result == [(services[0], 50000)]


def test_resolve_local_ports_empty_services():
    """Returns an empty list when no services are provided."""
    assert ensure_local_ports([], []) == []


def test_make_table_has_one_row_per_process():
    """Returns a table with one row per process."""
    procs = [
        _make_process("svc-a", remote_port=80, local_port=9000),
        _make_process("svc-b", remote_port=8080, local_port=9001),
    ]
    statuses = {"svc-a:80": "live", "svc-b:8080": "live"}
    table = make_table(procs, statuses, context=None)
    assert table.row_count == 2


def test_watch_processes_updates_status_on_exit():
    """Updates the status dict to 'died (exit N)' when a process exits."""
    proc = _make_process("svc", remote_port=80, local_port=9000, returncode=1)
    statuses: dict[str, str] = {"svc:80": "live"}

    asyncio.run(watch_processes([proc], statuses, asyncio.Event()))

    assert statuses["svc:80"] == "died (exit 1)"


def test_watch_processes_skips_update_when_stopped():
    """Does not update status when stop_event is already set."""
    proc = _make_process("svc", remote_port=80, local_port=9000, returncode=1)
    statuses: dict[str, str] = {"svc:80": "live"}
    stop_event = asyncio.Event()
    stop_event.set()

    asyncio.run(watch_processes([proc], statuses, stop_event))

    assert statuses["svc:80"] == "live"
