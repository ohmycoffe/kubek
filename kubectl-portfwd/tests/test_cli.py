import signal
from pathlib import Path

import pytest
from kubek.term.output import create_output
from portfwd.application.port_forwarding.events import PortForwardStarted
from portfwd.application.port_forwarding.streamer import (
    Backoff,
    PortForwardEventStreamer,
)
from portfwd.application.use_case import PortForwardUseCase
from portfwd.presentation.cli import run_port_forwards_from_cli
from portfwd.presentation.display import PortForwardLiveDisplay
from portfwd.presentation.spec_parser import parse_spec
from portfwd_test_utils.fakes import (
    NAMESPACE,
    FakeLaunch,
    PlannedLauncher,
    RecordingSleep,
    rendered_rows_by_name,
)

_NO_BACKOFF = Backoff(min_s=0, max_s=0)


def _make_use_case(launcher: PlannedLauncher, api) -> PortForwardUseCase:
    streamer = PortForwardEventStreamer(
        launcher,
        backoff=_NO_BACKOFF,
        sleep_for=RecordingSleep(),
        is_local_port_free=lambda port: True,
    )
    return PortForwardUseCase(streamer=streamer, api=api)


def test_run_port_forwards_raises_when_file_and_target_both_provided(fake_api):
    """file and target flags are mutually exclusive at the dispatch layer."""
    use_case = _make_use_case(PlannedLauncher({}), fake_api)

    with pytest.raises(ValueError, match="cannot both be provided"):
        run_port_forwards_from_cli(
            file=Path("forwards"),
            target=["ns/svc/svc:80::8080"],
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
    selected = parse_spec(f"{NAMESPACE}/svc/svc-foo:30::3030")
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

    assert set(rendered_rows_by_name(display)) == {"svc-foo"}


@pytest.mark.asyncio
async def test_stream_forwards_selected_pod(fake_api, captured_signal_handlers):
    """Streaming a selected pod renders it as a row in the live display."""
    selected = parse_spec(f"{NAMESPACE}/pod/pod-foo:50::5050")
    use_case = _make_use_case(
        PlannedLauncher(
            {"pod-foo": [FakeLaunch(pid=321, returncode=0, block_exit=True)]}
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

    assert set(rendered_rows_by_name(display)) == {"pod-foo"}


@pytest.mark.asyncio
async def test_stream_forwards_selected_deployment(fake_api, captured_signal_handlers):
    """Streaming a selected deployment renders it as a row in the live display."""
    selected = parse_spec(f"{NAMESPACE}/deployment/deploy-foo:70::7070")
    use_case = _make_use_case(
        PlannedLauncher(
            {"deploy-foo": [FakeLaunch(pid=456, returncode=0, block_exit=True)]}
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

    assert set(rendered_rows_by_name(display)) == {"deploy-foo"}
