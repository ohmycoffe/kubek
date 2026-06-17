from portfwd.application.port_forwarding.events import (
    OutputLine,
    OutputStream,
    PortForwardDied,
    PortForwardLaunchFailed,
    PortForwardOutput,
    PortForwardReconnecting,
    PortForwardStarted,
    PortForwardStopped,
)
from portfwd.application.port_forwarding.snapshot import PortForwardProcessSnapshot
from portfwd.presentation.display import (
    PortForwardLiveDisplay,
    _LogPanel,
    _PortForwardStatusTable,
)
from portfwd_test_utils.fakes import COL_PID, COL_STATUS
from rich.console import Console

_CONSOLE = Console()


def _make_snapshot(
    service_name: str,
    remote_port: int = 80,
    local_port: int = 9000,
    pid: int = 1234,
    returncode: int | None = None,
) -> PortForwardProcessSnapshot:
    return PortForwardProcessSnapshot(
        namespace="ns",
        service_name=service_name,
        remote_port=remote_port,
        local_port=local_port,
        pid=pid,
        returncode=returncode,
    )


def _make_event(
    event_cls: type[PortForwardStarted | PortForwardStopped | PortForwardDied],
    service_name: str,
    remote_port: int = 80,
    local_port: int = 9000,
    pid: int = 1234,
    returncode: int | None = None,
) -> PortForwardStarted | PortForwardStopped | PortForwardDied:
    return event_cls(
        snapshot=_make_snapshot(
            service_name,
            remote_port=remote_port,
            local_port=local_port,
            pid=pid,
            returncode=returncode,
        ),
    )


def test_status_table_has_one_row_per_tracked_snapshot():
    """render() returns one row per tracked process."""
    table = _PortForwardStatusTable(context=None)
    table.track(_make_snapshot("svc-a", pid=1))
    table.track(_make_snapshot("svc-b", pid=2))
    assert table.render().row_count == 2


def test_apply_started_tracks_a_new_row():
    """apply(STARTED) adds a row to the display table."""
    display = PortForwardLiveDisplay(context=None, console=_CONSOLE)
    display.apply(_make_event(PortForwardStarted, "svc"))
    assert display._table.render().row_count == 1


def test_apply_started_shows_live_status():
    """apply(STARTED) renders the row as live."""
    display = PortForwardLiveDisplay(context=None, console=_CONSOLE)
    display.apply(_make_event(PortForwardStarted, "svc"))

    cells = list(display._table.render().columns[-1].cells)
    assert "live" in str(cells[0])


def test_apply_started_multiple_services_track_separate_rows():
    """Each STARTED event for a different service adds a distinct row."""
    display = PortForwardLiveDisplay(context=None, console=_CONSOLE)
    display.apply(_make_event(PortForwardStarted, "svc-a", pid=1))
    display.apply(_make_event(PortForwardStarted, "svc-b", pid=2))
    assert display._table.render().row_count == 2


def test_apply_started_updates_existing_row_on_restart():
    """A second STARTED for the same service reuses the row and updates the PID."""
    display = PortForwardLiveDisplay(context=None, console=_CONSOLE)
    display.apply(_make_event(PortForwardStarted, "svc", pid=111))
    display.apply(
        _make_event(
            PortForwardDied,
            "svc",
            pid=111,
            returncode=1,
        )
    )
    display.apply(_make_event(PortForwardStarted, "svc", pid=222))

    assert display._table.render().row_count == 1
    pid_cells = list(display._table.render().columns[COL_PID].cells)
    status_cells = list(display._table.render().columns[COL_STATUS].cells)
    assert str(pid_cells[0]) == "222"
    assert "live" in str(status_cells[0])


def test_apply_stopped_marks_row_as_stopped():
    """apply(STOPPED) transitions the row status to stopped."""
    display = PortForwardLiveDisplay(context=None, console=_CONSOLE)
    display.apply(_make_event(PortForwardStarted, "svc"))

    display.apply(
        _make_event(
            PortForwardStopped,
            "svc",
            returncode=0,
        )
    )

    cells = list(display._table.render().columns[-1].cells)
    assert "stopped" in str(cells[0])


def _make_output_event(
    service_name: str,
    line: str,
    stream: OutputStream,
    local_port: int = 9000,
) -> PortForwardOutput:
    return PortForwardOutput(
        snapshot=_make_snapshot(service_name, local_port=local_port),
        output=OutputLine(stream=stream, text=line),
    )


def test_log_panel_shows_placeholder_when_empty():
    """An empty panel renders a waiting placeholder, not a blank line."""
    panel = _LogPanel()
    assert "Waiting for output" in str(panel.render(height=5).renderable)


def test_log_panel_records_line_with_source_tag():
    """A captured line is shown alongside its service:local_port source tag."""
    panel = _LogPanel()
    panel.append(
        _make_snapshot("svc-a", local_port=5000),
        OutputLine(stream=OutputStream.STDOUT, text="Forwarding from 127.0.0.1:5000"),
    )
    rendered = str(panel.render(height=5).renderable)
    assert "svc-a:5000" in rendered
    assert "Forwarding from 127.0.0.1:5000" in rendered


def test_log_panel_keeps_constant_height_with_bottom_padding():
    """The panel renders a fixed number of rows from the start (padded at the bottom)."""
    panel = _LogPanel()
    rendered_empty = str(panel.render(height=5).renderable)
    assert rendered_empty.count("\n") + 1 == 5

    panel.append(
        _make_snapshot("svc"),
        OutputLine(stream=OutputStream.STDOUT, text="first"),
    )
    rendered_one = str(panel.render(height=5).renderable)
    assert rendered_one.count("\n") + 1 == 5
    assert rendered_one.splitlines()[0].endswith("first")


def test_log_panel_renders_only_the_most_recent_lines():
    """When more lines arrive than fit, the newest (last N) are shown, not the first."""
    panel = _LogPanel()
    for i in range(10):
        panel.append(
            _make_snapshot("svc"),
            OutputLine(stream=OutputStream.STDOUT, text=f"line-{i}"),
        )

    rendered = str(panel.render(height=3).renderable)
    assert "line-9" in rendered
    assert "line-7" in rendered
    assert "line-6" not in rendered
    assert "line-0" not in rendered


def test_apply_output_appends_to_log_panel():
    """apply(OUTPUT) routes the real subprocess line into the logs panel."""
    display = PortForwardLiveDisplay(context=None, console=_CONSOLE)
    display.apply(_make_event(PortForwardStarted, "svc"))
    display.apply(
        _make_output_event("svc", "Handling connection for 9000", OutputStream.STDERR)
    )

    assert "Handling connection for 9000" in str(
        display._logs.render(height=5).renderable
    )


def test_apply_launch_failed_shows_reason_in_log_panel():
    """apply(LAUNCH_FAILED) appends a tagged error line to the logs panel."""
    display = PortForwardLiveDisplay(context=None, console=_CONSOLE)

    display.apply(
        PortForwardLaunchFailed(
            namespace="ns",
            service_name="svc-a",
            remote_port=80,
            local_port=5000,
            reason="kubectl exited with code 1",
        )
    )

    rendered = str(display._logs.render(height=5).renderable)
    assert "svc-a:5000" in rendered
    assert "kubectl exited with code 1" in rendered


def test_apply_lifecycle_events_are_logged_to_panel():
    """STARTED/DIED/STOPPED each append a history line to the logs panel."""
    display = PortForwardLiveDisplay(context=None, console=_CONSOLE)

    display.apply(_make_event(PortForwardStarted, "svc", pid=7))
    display.apply(_make_event(PortForwardDied, "svc", pid=7, returncode=2))
    display.apply(_make_event(PortForwardStarted, "svc", pid=9))
    display.apply(_make_event(PortForwardStopped, "svc", pid=9, returncode=0))

    rendered = str(display._logs.render(height=10).renderable)
    assert "port-forward started" in rendered
    assert "port-forward died (exit 2)" in rendered
    assert "port-forward stopped" in rendered


def test_apply_reconnecting_marks_row_and_logs_wait():
    """apply(RECONNECTING) flips the row to reconnecting and logs the busy port."""
    display = PortForwardLiveDisplay(context=None, console=_CONSOLE)
    display.apply(_make_event(PortForwardStarted, "svc", pid=7))
    display.apply(_make_event(PortForwardDied, "svc", pid=7, returncode=1))

    display.apply(
        PortForwardReconnecting(
            namespace="ns",
            service_name="svc",
            remote_port=80,
            local_port=9000,
        )
    )

    status_cells = list(display._table.render().columns[COL_STATUS].cells)
    assert "reconnecting" in str(status_cells[0])
    assert "local port 9000 in use" in str(display._logs.render(height=5).renderable)


def test_apply_reconnecting_logs_each_attempt():
    """Each RECONNECTING event appends another line to the logs panel."""
    display = PortForwardLiveDisplay(context=None, console=_CONSOLE)
    display.apply(_make_event(PortForwardStarted, "svc", pid=7))
    display.apply(_make_event(PortForwardDied, "svc", pid=7, returncode=1))

    reconnect = PortForwardReconnecting(
        namespace="ns",
        service_name="svc",
        remote_port=80,
        local_port=9000,
    )
    display.apply(reconnect)
    display.apply(reconnect)

    rendered = str(display._logs.render(height=10).renderable)
    assert rendered.count("local port 9000 in use") == 2


def test_apply_died_marks_row_as_died_with_exit_code():
    """apply(DIED) transitions the row to died and includes the exit code."""
    display = PortForwardLiveDisplay(context=None, console=_CONSOLE)
    display.apply(_make_event(PortForwardStarted, "svc"))

    display.apply(
        _make_event(
            PortForwardDied,
            "svc",
            returncode=1,
        )
    )

    cells = list(display._table.render().columns[-1].cells)
    cell_text = str(cells[0])
    assert "died" in cell_text
    assert "1" in cell_text
