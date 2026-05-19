import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from portfwd.config import PortFwdConfig, ServicePortForwardDefaults
from portfwd.kube import PortForwardProcess
from portfwd.plan import resolve_local_port
from portfwd.runner import watch_processes
from portfwd.term.display import make_table
from portfwd.utils import get_port_forward_status_id


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


_SVC_CONFIG = ServicePortForwardDefaults(
    name="svc", namespace="ns", remote_port=80, local_port=9000
)


def test_resolve_local_port_uses_configured_port():
    """Returns the configured local_port when a matching config entry exists."""
    config = PortFwdConfig(defaults=[_SVC_CONFIG])
    result = resolve_local_port("svc", "ns", 80, config)
    assert result == 9000


def test_resolve_local_port_uses_deterministic_port_when_free():
    """Returns the deterministic port when no config match and the port is free."""
    config = PortFwdConfig()
    with (
        patch("portfwd.plan.get_deterministic_port", return_value=55000),
        patch("portfwd.plan.is_port_free", return_value=True),
    ):
        result = resolve_local_port("svc", "ns", 80, config)
    assert result == 55000


def test_resolve_local_port_falls_back_to_free_port_when_deterministic_taken():
    """Falls back to find_free_port when the deterministic port is already in use."""
    config = PortFwdConfig()
    with (
        patch("portfwd.plan.get_deterministic_port", return_value=55000),
        patch("portfwd.plan.is_port_free", return_value=False),
        patch("portfwd.plan.find_free_port", return_value=50000),
    ):
        result = resolve_local_port("svc", "ns", 80, config)
    assert result == 50000


def test_resolve_local_port_ignores_config_from_other_namespace():
    """Does not use a config entry whose namespace does not match."""
    other_ns = ServicePortForwardDefaults(
        name="svc", namespace="other-ns", remote_port=80, local_port=9000
    )
    config = PortFwdConfig(defaults=[other_ns])
    with (
        patch("portfwd.plan.get_deterministic_port", return_value=55000),
        patch("portfwd.plan.is_port_free", return_value=False),
        patch("portfwd.plan.find_free_port", return_value=50000),
    ):
        result = resolve_local_port("svc", "ns", 80, config)
    assert result == 50000


def test_make_table_has_one_row_per_process():
    """Returns a table with one row per process."""
    procs = [
        _make_process("svc-a", remote_port=80, local_port=9000),
        _make_process("svc-b", remote_port=8080, local_port=9001),
    ]
    statuses = {
        get_port_forward_status_id(
            namespace="ns", service_name="svc-a", remote_port=80
        ): "live",
        get_port_forward_status_id(
            namespace="ns", service_name="svc-b", remote_port=8080
        ): "live",
    }
    table = make_table(procs, statuses, context=None)
    assert table.row_count == 2


def test_watch_processes_updates_status_on_exit():
    """Updates the status dict to 'died (exit N)' when a process exits."""
    proc = _make_process("svc", remote_port=80, local_port=9000, returncode=1)
    row_id = get_port_forward_status_id(
        namespace="ns", service_name="svc", remote_port=80
    )
    statuses: dict[str, str] = {row_id: "live"}

    asyncio.run(watch_processes([proc], statuses, asyncio.Event()))

    assert statuses[row_id] == "died (exit 1)"


def test_watch_processes_skips_update_when_stopped():
    """Does not update status when stop_event is already set."""
    proc = _make_process("svc", remote_port=80, local_port=9000, returncode=1)
    row_id = get_port_forward_status_id(
        namespace="ns", service_name="svc", remote_port=80
    )
    statuses: dict[str, str] = {row_id: "live"}
    stop_event = asyncio.Event()
    stop_event.set()

    asyncio.run(watch_processes([proc], statuses, stop_event))

    assert statuses[row_id] == "live"
