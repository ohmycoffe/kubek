import asyncio
import signal

import pytest
from portfwd.application.port_forwarding.events import (
    OutputLine,
    OutputStream,
    PortForwardDied,
    PortForwardLaunchAbandoned,
    PortForwardLaunchFailed,
    PortForwardLocalPortBusy,
    PortForwardOutput,
    PortForwardReconnecting,
    PortForwardShutdownWhileWaiting,
    PortForwardStarted,
    PortForwardStopped,
)
from portfwd.application.port_forwarding.streamer import (
    Backoff,
    PortForwardEventStreamer,
)
from portfwd.domain.models import (
    PortForwardPlan,
    ResolvedTargetRef,
    TargetKind,
)
from portfwd_test_utils.fakes import (
    FailingLauncher,
    FakeSession,
    ScriptedPortChecker,
    SequentialLauncher,
    StaticLauncher,
    make_snapshot,
)

_PLAN_LOCAL_PORT = 9000
PLAN = PortForwardPlan(
    target=ResolvedTargetRef(kind=TargetKind.SERVICE, namespace="ns", name="svc"),
    remote_port=80,
    local_port=_PLAN_LOCAL_PORT,
)

_NO_BACKOFF = Backoff(min_s=0, max_s=0)


def _make_streamer(
    launcher,
    *,
    backoff: Backoff = _NO_BACKOFF,
    is_local_port_free=None,
) -> PortForwardEventStreamer:
    return PortForwardEventStreamer(
        launcher,
        backoff=backoff,
        is_local_port_free=is_local_port_free or (lambda port: True),
    )


@pytest.mark.asyncio
async def test_stream_yields_nothing_when_plans_empty():
    """No events are yielded when there are no plans to run."""
    streamer = _make_streamer(StaticLauncher(FakeSession(make_snapshot())))

    events = [event async for event in streamer.stream([])]

    assert events == []


@pytest.mark.asyncio
async def test_stream_retries_launch_until_process_starts(captured_signal_handlers):
    """Launch failures are retried (and surfaced) until a subprocess starts."""
    launcher = FailingLauncher(fail_count=2)
    streamer = _make_streamer(launcher)

    events = []
    async for event in streamer.stream([PLAN]):
        events.append(event)
        if isinstance(event, PortForwardStarted):
            captured_signal_handlers[signal.SIGINT]()

    types = [type(event) for event in events]
    assert launcher.attempts == 3
    assert types.count(PortForwardLaunchFailed) == 2
    assert PortForwardStarted in types
    assert isinstance(events[-1], PortForwardStopped)


@pytest.mark.asyncio
async def test_launch_failed_event_carries_target_and_reason(captured_signal_handlers):
    """A LAUNCH_FAILED event names the forward and the underlying error."""
    streamer = _make_streamer(FailingLauncher(fail_count=1))

    failures = []
    async for event in streamer.stream([PLAN]):
        if isinstance(event, PortForwardLaunchFailed):
            failures.append(event)
        if isinstance(event, PortForwardStarted):
            captured_signal_handlers[signal.SIGINT]()

    assert len(failures) == 1
    assert failures[0].name == PLAN.target.name
    assert failures[0].local_port == PLAN.local_port
    assert "launch failed" in failures[0].reason


@pytest.mark.asyncio
async def test_stream_yields_died_then_restarts_on_unexpected_exit(
    captured_signal_handlers,
):
    """DIED is yielded and the same plan is relaunched when a process exits unexpectedly."""
    first = FakeSession(
        make_snapshot(local_port=_PLAN_LOCAL_PORT, pid=111, returncode=1)
    )
    second = FakeSession(
        make_snapshot(local_port=_PLAN_LOCAL_PORT, pid=222, returncode=0),
        block_exit=True,
    )
    streamer = _make_streamer(SequentialLauncher([first, second]))

    events = []
    async for event in streamer.stream([PLAN]):
        events.append(event)
        started = sum(1 for e in events if isinstance(e, PortForwardStarted))
        if started == 2:
            captured_signal_handlers[signal.SIGINT]()

    assert [type(event) for event in events] == [
        PortForwardStarted,
        PortForwardDied,
        PortForwardReconnecting,
        PortForwardStarted,
        PortForwardStopped,
    ]
    assert events[0].snapshot.pid == 111
    assert events[3].snapshot.pid == 222
    assert events[0].snapshot.local_port == PLAN.local_port
    assert events[3].snapshot.local_port == PLAN.local_port


@pytest.mark.asyncio
async def test_stream_yields_output_events_from_subprocess_streams(
    captured_signal_handlers,
):
    """OUTPUT events carry real stdout/stderr lines and don't end the stream early."""
    session = FakeSession(
        make_snapshot(),
        block_exit=True,
        output=[
            OutputLine(stream=OutputStream.STDOUT, text="Forwarding from 127.0.0.1"),
            OutputLine(stream=OutputStream.STDERR, text="lost connection to pod"),
        ],
    )
    streamer = _make_streamer(StaticLauncher(session))

    events = []
    async for event in streamer.stream([PLAN]):
        events.append(event)
        if isinstance(event, PortForwardOutput):
            captured_signal_handlers[signal.SIGINT]()

    outputs = [e for e in events if isinstance(e, PortForwardOutput)]
    assert {(o.output.stream, o.output.text) for o in outputs} == {
        (OutputStream.STDOUT, "Forwarding from 127.0.0.1"),
        (OutputStream.STDERR, "lost connection to pod"),
    }
    assert isinstance(events[-1], PortForwardStopped)


@pytest.mark.asyncio
async def test_stream_yields_stopped_when_shutdown_expected(captured_signal_handlers):
    """STOPPED is yielded when the process exits after an expected shutdown."""
    streamer = _make_streamer(
        StaticLauncher(FakeSession(make_snapshot(returncode=0), block_exit=True))
    )

    events = []
    async for event in streamer.stream([PLAN]):
        events.append(event)
        if isinstance(event, PortForwardStarted):
            captured_signal_handlers[signal.SIGINT]()  # simulate Ctrl+C

    assert isinstance(events[0], PortForwardStarted)
    assert isinstance(events[-1], PortForwardStopped)


@pytest.mark.asyncio
async def test_stream_waits_for_local_port_before_restarting(captured_signal_handlers):
    """Restart polls until the local port is released, sleeping the poll delay.

    Launch retries use a persistent backoff across restarts; port-busy polls
    use a separate counter that resets on each wait.
    """
    first = FakeSession(
        make_snapshot(local_port=_PLAN_LOCAL_PORT, pid=111, returncode=1)
    )
    second = FakeSession(
        make_snapshot(local_port=_PLAN_LOCAL_PORT, pid=222, returncode=0),
        block_exit=True,
    )
    # First launch: port free. Restart: busy twice, then free.
    port_checker = ScriptedPortChecker([True, False, False, True])
    streamer = _make_streamer(
        SequentialLauncher([first, second]),
        backoff=Backoff(min_s=0, max_s=0),
        is_local_port_free=port_checker,
    )

    started = 0
    types = []
    async for event in streamer.stream([PLAN]):
        types.append(type(event))
        if isinstance(event, PortForwardStarted):
            started += 1
            if started == 2:
                captured_signal_handlers[signal.SIGINT]()

    assert port_checker.calls == 4
    assert types.count(PortForwardReconnecting) == 1
    assert types.count(PortForwardLocalPortBusy) == 2


@pytest.mark.asyncio
async def test_stream_yields_shutdown_when_shutdown_during_port_poll(
    captured_signal_handlers,
):
    """Ctrl+C while waiting for a busy local port emits SHUTDOWN_WHILE_WAITING."""
    first = FakeSession(
        make_snapshot(local_port=_PLAN_LOCAL_PORT, pid=111, returncode=1)
    )
    port_checker = ScriptedPortChecker([True, False])
    streamer = _make_streamer(
        SequentialLauncher([first]),
        backoff=Backoff(min_s=0, max_s=0),
        is_local_port_free=port_checker,
    )

    events = []
    async for event in streamer.stream([PLAN]):
        events.append(event)
        if isinstance(event, PortForwardLocalPortBusy):
            captured_signal_handlers[signal.SIGINT]()

    assert isinstance(events[-1], PortForwardShutdownWhileWaiting)
    assert events[-1].name == PLAN.target.name
    assert events[-1].local_port == PLAN.local_port


@pytest.mark.asyncio
async def test_sleep_or_shutdown_returns_before_timeout():
    """Shutdown ends the wait before the timeout elapses."""
    streamer = _make_streamer(
        StaticLauncher(FakeSession(make_snapshot(), block_exit=True)),
    )
    expected_shutdown = asyncio.Event()

    wait_task = asyncio.create_task(
        streamer._sleep_or_shutdown(3600.0, expected_shutdown)
    )
    await asyncio.sleep(0)
    expected_shutdown.set()
    await asyncio.wait_for(wait_task, timeout=0.1)


@pytest.mark.asyncio
async def test_stream_stops_after_max_retries_on_crash_loop():
    """Unexpected exits stop restarting once ``Backoff.max_retries`` is exhausted."""
    dying = FakeSession(make_snapshot(returncode=1))
    streamer = _make_streamer(
        StaticLauncher(dying),
        backoff=Backoff(min_s=0, max_s=0, max_retries=2),
    )

    events = [event async for event in streamer.stream([PLAN])]

    assert [type(event) for event in events] == [
        PortForwardStarted,
        PortForwardDied,
        PortForwardReconnecting,
        PortForwardStarted,
        PortForwardDied,
        PortForwardLaunchAbandoned,
    ]


@pytest.mark.asyncio
async def test_stream_stops_after_max_launch_failures():
    """Launch failures stop retrying once ``Backoff.max_retries`` is exhausted."""
    streamer = _make_streamer(
        FailingLauncher(fail_count=10),
        backoff=Backoff(min_s=0, max_s=0, max_retries=2),
    )

    events = [event async for event in streamer.stream([PLAN])]

    assert [type(event) for event in events] == [
        PortForwardLaunchFailed,
        PortForwardReconnecting,
        PortForwardLaunchFailed,
        PortForwardLaunchAbandoned,
    ]
