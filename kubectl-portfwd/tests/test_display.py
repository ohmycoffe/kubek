from portfwd.application.port_forwarding.events import (
    OutputLine,
    OutputStream,
    PortForwardEvent,
    PortForwardEventType,
)
from portfwd.application.port_forwarding.snapshot import PortForwardProcessSnapshot
from portfwd.presentation.display import (
    PortForwardLiveDisplay,
    _LogPanel,
    _PortForwardStatusTable,
)
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
    event_type: PortForwardEventType,
    service_name: str,
    remote_port: int = 80,
    local_port: int = 9000,
    pid: int = 1234,
    returncode: int | None = None,
) -> PortForwardEvent:
    return PortForwardEvent(
        type=event_type,
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
    display.apply(_make_event(PortForwardEventType.STARTED, "svc"))
    assert display._table.render().row_count == 1


def test_apply_started_shows_live_status():
    """apply(STARTED) renders the row as live."""
    display = PortForwardLiveDisplay(context=None, console=_CONSOLE)
    display.apply(_make_event(PortForwardEventType.STARTED, "svc"))

    cells = list(display._table.render().columns[-1].cells)
    assert "live" in str(cells[0])


def test_apply_started_multiple_times_tracks_all_rows():
    """Each STARTED event adds a distinct row."""
    display = PortForwardLiveDisplay(context=None, console=_CONSOLE)
    display.apply(_make_event(PortForwardEventType.STARTED, "svc-a", pid=1))
    display.apply(_make_event(PortForwardEventType.STARTED, "svc-b", pid=2))
    assert display._table.render().row_count == 2


def test_apply_stopped_marks_row_as_stopped():
    """apply(STOPPED) transitions the row status to stopped."""
    display = PortForwardLiveDisplay(context=None, console=_CONSOLE)
    display.apply(_make_event(PortForwardEventType.STARTED, "svc"))

    display.apply(
        _make_event(
            PortForwardEventType.STOPPED,
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
) -> PortForwardEvent:
    return PortForwardEvent(
        type=PortForwardEventType.OUTPUT,
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
    display.apply(_make_event(PortForwardEventType.STARTED, "svc"))
    display.apply(
        _make_output_event("svc", "Handling connection for 9000", OutputStream.STDERR)
    )

    assert "Handling connection for 9000" in str(
        display._logs.render(height=5).renderable
    )


def test_apply_died_marks_row_as_died_with_exit_code():
    """apply(DIED) transitions the row to died and includes the exit code."""
    display = PortForwardLiveDisplay(context=None, console=_CONSOLE)
    display.apply(_make_event(PortForwardEventType.STARTED, "svc"))

    display.apply(
        _make_event(
            PortForwardEventType.DIED,
            "svc",
            returncode=1,
        )
    )

    cells = list(display._table.render().columns[-1].cells)
    cell_text = str(cells[0])
    assert "died" in cell_text
    assert "1" in cell_text
