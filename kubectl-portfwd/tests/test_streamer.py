import asyncio
import signal
from collections.abc import AsyncIterator
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from portfwd.application.port_forwarding.events import (
    OutputLine,
    OutputStream,
    PortForwardEventType,
)
from portfwd.application.port_forwarding.snapshot import PortForwardProcessSnapshot
from portfwd.application.port_forwarding.streamer import PortForwardEventStreamer
from portfwd.application.ports import PortForwardLauncher, PortForwardSession
from portfwd.domain.errors import PortForwardStartError
from portfwd.domain.models import NamespacedServiceNamePlan, ServicePortForwardPlan

_PLAN = ServicePortForwardPlan(
    target=NamespacedServiceNamePlan(namespace="ns", name="svc"),
    remote_port=80,
    local_port=9000,
)


class FakeSession(PortForwardSession):
    """Session that exits immediately, or blocks until terminate() is called."""

    def __init__(
        self,
        *,
        returncode: int | None,
        block_exit: bool = False,
        output: list[OutputLine] | None = None,
    ) -> None:
        self._returncode = returncode
        self._exit = asyncio.Event()
        self._output = output or []
        if not block_exit:
            self._exit.set()

    async def stream_output(self) -> AsyncIterator[OutputLine]:
        for line in self._output:
            yield line

    def snapshot(self) -> PortForwardProcessSnapshot:
        return PortForwardProcessSnapshot(
            namespace="ns",
            service_name="svc",
            remote_port=80,
            local_port=9000,
            pid=1234,
            returncode=self._returncode,
        )

    async def wait(self) -> None:
        await self._exit.wait()

    def terminate(self) -> None:
        self._exit.set()


class FakeLauncher(PortForwardLauncher):
    def __init__(self, session: PortForwardSession) -> None:
        self._session = session

    async def launch(self, plan: ServicePortForwardPlan) -> PortForwardSession:
        return self._session


class FailingLauncher(PortForwardLauncher):
    async def launch(self, plan: ServicePortForwardPlan) -> PortForwardSession:
        raise RuntimeError("launch failed")


@contextmanager
def _capture_signal_handlers():
    """
    Record signal handlers instead of registering them with the event loop.

    Note:
    The streamer registers real SIGINT/SIGTERM handlers on the event loop. In tests we
    intercept those calls, store the callbacks, and invoke them manually (see STOPPED test).
    """
    handlers: dict[int, object] = {}
    loop = asyncio.get_running_loop()

    def register(sig: int, callback: object) -> None:
        handlers[sig] = callback

    with (
        patch.object(loop, "add_signal_handler", side_effect=register),
        patch.object(loop, "remove_signal_handler"),
    ):
        yield handlers


@pytest.mark.asyncio
async def test_stream_yields_nothing_when_plans_empty():
    """No events are yielded when there are no plans to run."""
    launcher = FakeLauncher(FakeSession(returncode=0))

    with _capture_signal_handlers():
        streamer = PortForwardEventStreamer(launcher)
        events = [event async for event in streamer.stream_port_forwards([])]

    assert events == []


@pytest.mark.asyncio
async def test_stream_raises_port_forward_start_error_when_launch_fails():
    """PortForwardStartError is raised when kubectl launch fails."""
    with _capture_signal_handlers():
        streamer = PortForwardEventStreamer(FailingLauncher())

        with pytest.raises(PortForwardStartError, match="failed to start"):
            async for _ in streamer.stream_port_forwards([_PLAN]):
                pass


@pytest.mark.asyncio
async def test_stream_yields_died_when_process_exits_unexpectedly():
    """DIED is yielded when the process exits and shutdown was not expected."""
    launcher = FakeLauncher(FakeSession(returncode=1))

    with _capture_signal_handlers():
        streamer = PortForwardEventStreamer(launcher)

        events = [event async for event in streamer.stream_port_forwards([_PLAN])]

    assert events[0].type == PortForwardEventType.STARTED
    assert events[-1].type == PortForwardEventType.DIED
    assert events[-1].snapshot.returncode == 1


@pytest.mark.asyncio
async def test_stream_yields_output_events_from_subprocess_streams():
    """OUTPUT events carry real stdout/stderr lines and don't end the stream early."""
    session = FakeSession(
        returncode=0,
        output=[
            OutputLine(stream=OutputStream.STDOUT, text="Forwarding from 127.0.0.1"),
            OutputLine(stream=OutputStream.STDERR, text="lost connection to pod"),
        ],
    )
    launcher = FakeLauncher(session)

    with _capture_signal_handlers():
        streamer = PortForwardEventStreamer(launcher)
        events = [event async for event in streamer.stream_port_forwards([_PLAN])]

    outputs = [e for e in events if e.type == PortForwardEventType.OUTPUT]
    assert {(o.output.stream, o.output.text) for o in outputs if o.output} == {
        (OutputStream.STDOUT, "Forwarding from 127.0.0.1"),
        (OutputStream.STDERR, "lost connection to pod"),
    }
    assert any(e.type == PortForwardEventType.DIED for e in events)


@pytest.mark.asyncio
async def test_stream_yields_stopped_when_shutdown_expected():
    """STOPPED is yielded when the process exits after an expected shutdown."""
    launcher = FakeLauncher(FakeSession(returncode=0, block_exit=True))

    with _capture_signal_handlers() as handlers:
        events = []
        streamer = PortForwardEventStreamer(launcher)
        async for event in streamer.stream_port_forwards([_PLAN]):
            events.append(event)
            if event.type == PortForwardEventType.STARTED:
                handlers[signal.SIGINT]()  # simulate Ctrl+C

    assert events[0].type == PortForwardEventType.STARTED
    assert events[-1].type == PortForwardEventType.STOPPED
