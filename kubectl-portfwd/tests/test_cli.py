import signal
from pathlib import Path

import pytest
from kubek.term.output import create_output
from portfwd.application.port_forwarding.events import PortForwardStarted
from portfwd.application.port_forwarding.streamer import (
    PortForwardEventStreamer,
    RestartDelays,
)
from portfwd.application.use_case import PortForwardUseCase
from portfwd.presentation.cli import run_port_forwards_from_cli
from portfwd.presentation.display import PortForwardLiveDisplay
from portfwd.presentation.service_parser import parse_spec
from portfwd_test_utils.fakes import (
    NAMESPACE,
    FakeLaunch,
    PlannedLauncher,
    RecordingSleep,
    rendered_rows_by_service,
)

_INSTANT_DELAYS = RestartDelays(min_s=0, poll_s=0, max_s=0)


def _make_use_case(launcher: PlannedLauncher, api) -> PortForwardUseCase:
    streamer = PortForwardEventStreamer(
        launcher,
        restart_delays=_INSTANT_DELAYS,
        sleep_for=RecordingSleep(),
        is_local_port_free=lambda port: True,
    )
    return PortForwardUseCase(streamer=streamer, api=api)


def test_run_port_forwards_raises_when_file_and_service_both_provided(fake_api):
    """file and service flags are mutually exclusive at the dispatch layer."""
    use_case = _make_use_case(PlannedLauncher({}), fake_api)

    with pytest.raises(ValueError, match="cannot both be provided"):
        run_port_forwards_from_cli(
            file=Path("forwards"),
            service=["ns/svc:80::8080"],
            api=fake_api,
            out=create_output(),
            use_case=use_case,
            display=PortForwardLiveDisplay(
                context=None, console=create_output().console
            ),
        )


@pytest.mark.asyncio
async def test_stream_forwards_selected_service(fake_api, captured_signal_handlers):
    """Streaming a selected service renders it as a row in the live display."""
    selected = parse_spec(f"{NAMESPACE}/svc-foo:30::3030")
    use_case = _make_use_case(
        PlannedLauncher(
            {"svc-foo": [FakeLaunch(pid=123, returncode=0, block_exit=True)]}
        ),
        fake_api,
    )
    display = PortForwardLiveDisplay(
        context=fake_api.current_config.context,
        console=create_output().console,
    )

    with display.live():
        async for event in use_case.stream_specs([selected]):
            display.apply(event)
            if isinstance(event, PortForwardStarted):
                captured_signal_handlers[signal.SIGINT]()

    assert set(rendered_rows_by_service(display)) == {"svc-foo"}
