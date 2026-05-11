import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

from pfwd.cli.port_forward import ensure_local_ports, make_table, watch_processes
from pfwd.config import ServiceConfig
from pfwd.kube import KubernetesService, PortForwardProcess


def _make_service(name: str, port: int) -> KubernetesService:
    return KubernetesService(name=name, port=port, protocol="TCP")


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
    )


_SVC_CONFIG = ServiceConfig(name="svc", namespace="ns", remote_port=80, local_port=9000)


def test_resolve_local_ports_uses_preferred_port():
    """Uses the configured local port when the preferred port is available."""
    services = [_make_service("svc", 80)]

    with patch("pfwd.cli.port_forward.ensure_port", return_value=9000):
        result = ensure_local_ports(services, [_SVC_CONFIG], "ns")

    assert result == [(services[0], 9000)]


def test_resolve_local_ports_falls_back_when_preferred_unavailable(caplog):
    """Falls back to a free port and logs a warning when the preferred port is taken."""
    services = [_make_service("svc", 80)]

    with (
        caplog.at_level(logging.WARNING, logger="pfwd.cli.port_forward"),
        patch("pfwd.cli.port_forward.ensure_port", return_value=9001),
    ):
        result = ensure_local_ports(services, [_SVC_CONFIG], "ns")

    assert result == [(services[0], 9001)]
    assert "9000" in caplog.text
    assert "9001" in caplog.text


def test_resolve_local_ports_no_config_match():
    """Returns a free port when no config entry matches the service."""
    services = [_make_service("svc", 80)]

    with patch("pfwd.cli.port_forward.ensure_port", return_value=50000):
        result = ensure_local_ports(services, [], "ns")

    assert result == [(services[0], 50000)]


def test_resolve_local_ports_ignores_config_from_other_namespace():
    """Does not use config entries whose namespace does not match."""
    services = [_make_service("svc", 80)]
    other_ns = ServiceConfig(
        name="svc", namespace="other-ns", remote_port=80, local_port=9000
    )

    with patch("pfwd.cli.port_forward.ensure_port", return_value=50000):
        result = ensure_local_ports(services, [other_ns], "ns")

    assert result == [(services[0], 50000)]


def test_resolve_local_ports_empty_services():
    """Returns an empty list when no services are provided."""
    assert ensure_local_ports([], [], "ns") == []


def test_make_table_has_one_row_per_process():
    """Returns a table with one row per process."""
    procs = [
        _make_process("svc-a", remote_port=80, local_port=9000),
        _make_process("svc-b", remote_port=8080, local_port=9001),
    ]
    statuses = {"svc-a:80": "live", "svc-b:8080": "live"}
    table = make_table(procs, statuses, "ns", context=None)
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
