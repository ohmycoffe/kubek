import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from portfwd.config import PortFwdConfig, ServicePortForwardDefaults
from portfwd.display import LiveStatusTable
from portfwd.kubectl import PortForwardProcess
from portfwd.plan import resolve_local_port
from portfwd.runner import watch_processes


def _make_process(
    service_name: str, remote_port: int, local_port: int, returncode: int = 0
) -> PortForwardProcess:
    """Build a PortForwardProcess wrapping a mocked asyncio subprocess."""
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
    assert resolve_local_port("svc", "ns", 80, config) == 9000


def test_resolve_local_port_uses_deterministic_port_when_free():
    """Returns the deterministic port when no config match and the port is free."""
    config = PortFwdConfig()
    with (
        patch("portfwd.plan.get_deterministic_port", return_value=55000),
        patch("portfwd.plan.is_port_free", return_value=True),
    ):
        assert resolve_local_port("svc", "ns", 80, config) == 55000


def test_resolve_local_port_falls_back_to_free_port_when_deterministic_taken():
    """Falls back to find_free_port when the deterministic port is already in use."""
    config = PortFwdConfig()
    with (
        patch("portfwd.plan.get_deterministic_port", return_value=55000),
        patch("portfwd.plan.is_port_free", return_value=False),
        patch("portfwd.plan.find_free_port", return_value=50000),
    ):
        assert resolve_local_port("svc", "ns", 80, config) == 50000


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
        assert resolve_local_port("svc", "ns", 80, config) == 50000


def test_live_status_table_has_one_row_per_tracked_process():
    """LiveStatusTable.render() returns one row per tracked process."""
    table = LiveStatusTable(context=None)
    table.track(_make_process("svc-a", remote_port=80, local_port=9000))
    table.track(_make_process("svc-b", remote_port=8080, local_port=9001))
    assert table.render().row_count == 2


def test_watch_processes_marks_died_on_exit():
    """watch_processes marks a tracked process as 'died (exit N)' when it exits."""
    proc = _make_process("svc", remote_port=80, local_port=9000, returncode=1)
    table = LiveStatusTable()
    table.track(proc)

    asyncio.run(watch_processes([proc], table, asyncio.Event()))

    rendered = table.render()
    assert rendered.row_count == 1
    cells = list(rendered.columns[-1].cells)
    assert "died (exit 1)" in cells[0]


def test_watch_processes_skips_update_when_stopped():
    """watch_processes leaves status untouched when stop_event is already set."""
    proc = _make_process("svc", remote_port=80, local_port=9000, returncode=1)
    table = LiveStatusTable()
    table.track(proc)
    stop_event = asyncio.Event()
    stop_event.set()

    asyncio.run(watch_processes([proc], table, stop_event))

    cells = list(table.render().columns[-1].cells)
    assert "● live" in cells[0]
