import signal
from pathlib import Path

import pytest
from kubek.term.output import create_output
from kubek.term.style import Color
from portfwd.application.port_forwarding.events import PortForwardStarted
from portfwd.application.port_forwarding.streamer import (
    Backoff,
    PortForwardEventStreamer,
)
from portfwd.application.use_case import PortForwardUseCase
from portfwd.presentation.display import PortForwardLiveDisplay
from portfwd.presentation.spec_parser import parse_spec
from portfwd_test_utils.fakes import (
    COL_LOCAL,
    COL_NAMESPACE,
    COL_PID,
    COL_REMOTE,
    COL_STATUS,
    NAMESPACE,
    FakeLaunch,
    PlannedLauncher,
    build_services,
    rendered_rows_by_name,
)

_NO_BACKOFF = Backoff(min_s=0, max_s=0)
_STOPPED = f"[{Color.WARNING}]■ stopped[/{Color.WARNING}]"


def _make_use_case(launcher: PlannedLauncher, api) -> PortForwardUseCase:
    """Use case whose streamer never really sleeps or probes ports."""
    streamer = PortForwardEventStreamer(
        launcher,
        backoff=_NO_BACKOFF,
        is_local_port_free=lambda port: True,
    )
    return PortForwardUseCase(streamer=streamer, api=api)


def _spec(*, service: str, remote_port: int, local_port: int) -> str:
    return f"{NAMESPACE}/svc/{service}:{remote_port}::{local_port}"


async def _drive_until_started(
    *,
    use_case: PortForwardUseCase,
    display: PortForwardLiveDisplay,
    specs,
    started_target: int,
    handlers,
) -> None:
    """Apply events to the display, firing Ctrl+C once `started_target` STARTED seen."""
    started = 0
    with display.live():
        async for event in use_case.stream_specs(specs):
            display.apply(event)
            if isinstance(event, PortForwardStarted):
                started += 1
                if started == started_target:
                    handlers[signal.SIGINT]()


@pytest.mark.asyncio
async def test_run_from_spec_restarts_after_death(fake_api, captured_signal_handlers):
    """A dead port-forward is relaunched on the same local port until Ctrl+C."""
    foo, bar = build_services()
    foo_local, bar_local = 3030, 4040
    foo_restart_pid, bar_restart_pid = 789, 1011

    launcher = PlannedLauncher(
        {
            foo.metadata.name: [
                FakeLaunch(pid=123, returncode=1),
                FakeLaunch(pid=foo_restart_pid, returncode=0, block_exit=True),
            ],
            bar.metadata.name: [
                FakeLaunch(pid=456, returncode=10),
                FakeLaunch(pid=bar_restart_pid, returncode=0, block_exit=True),
            ],
        }
    )
    use_case = _make_use_case(launcher, fake_api)
    display = PortForwardLiveDisplay(
        context=fake_api.current_config.context,
        console=create_output().console,
    )
    specs = [
        parse_spec(
            _spec(service=foo.metadata.name, remote_port=30, local_port=foo_local)
        ),
        parse_spec(
            _spec(service=bar.metadata.name, remote_port=40, local_port=bar_local)
        ),
    ]

    await _drive_until_started(
        use_case=use_case,
        display=display,
        specs=specs,
        started_target=4,
        handlers=captured_signal_handlers,
    )

    rows = rendered_rows_by_name(display)
    assert rows[foo.metadata.name] == _row(
        service=foo.metadata.name, remote_port=30, local=foo_local, pid=foo_restart_pid
    )
    assert rows[bar.metadata.name] == _row(
        service=bar.metadata.name, remote_port=40, local=bar_local, pid=bar_restart_pid
    )


@pytest.mark.asyncio
async def test_run_from_spec_file(fake_api, captured_signal_handlers, tmp_path: Path):
    """Spec-file mode relaunches a dead port-forward on the same local port."""
    foo, _ = build_services()
    foo_local, foo_restart_pid = 3030, 789

    spec_file = tmp_path / ".portfwd-plan"
    spec_file.write_text(
        _spec(service=foo.metadata.name, remote_port=30, local_port=foo_local) + "\n",
        encoding="utf-8",
    )

    launcher = PlannedLauncher(
        {
            foo.metadata.name: [
                FakeLaunch(pid=123, returncode=1),
                FakeLaunch(pid=foo_restart_pid, returncode=0, block_exit=True),
            ],
        }
    )
    use_case = _make_use_case(launcher, fake_api)
    display = PortForwardLiveDisplay(
        context=fake_api.current_config.context,
        console=create_output().console,
    )
    # Read the spec back from the file to exercise the same parsing path the CLI uses.
    specs = [parse_spec(spec_file.read_text(encoding="utf-8").strip())]

    await _drive_until_started(
        use_case=use_case,
        display=display,
        specs=specs,
        started_target=2,
        handlers=captured_signal_handlers,
    )

    rows = rendered_rows_by_name(display)
    assert rows[foo.metadata.name] == _row(
        service=foo.metadata.name, remote_port=30, local=foo_local, pid=foo_restart_pid
    )


def _row(*, service: str, remote_port: int, local: int, pid: int) -> tuple[str, ...]:
    """Expected fully-rendered table row for a stopped, restarted forward."""
    cells = [""] * 5
    cells[COL_NAMESPACE] = NAMESPACE
    cells[COL_REMOTE] = f"svc/{service}:{remote_port}"
    cells[COL_LOCAL] = f"localhost:{local}"
    cells[COL_PID] = str(pid)
    cells[COL_STATUS] = _STOPPED
    return tuple(cells)
