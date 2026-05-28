from portfwd.application.port_forwarding.events import (
    PortForwardProcessSnapshot,
)
from portfwd.presentation.display import PortForwardLiveDisplay, _PortForwardStatusTable


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


def test_status_table_has_one_row_per_tracked_snapshot():
    """render() returns one row per tracked process."""
    table = _PortForwardStatusTable(context=None)
    table.track(_make_snapshot("svc-a", pid=1))
    table.track(_make_snapshot("svc-b", pid=2))
    assert table.render().row_count == 2


def test_started_tracks_a_new_row():
    """started() adds a row to the display table."""
    display = PortForwardLiveDisplay(context=None)
    display.started(_make_snapshot("svc"))
    assert display._table.render().row_count == 1


def test_started_multiple_times_tracks_all_rows():
    """Each started() call adds a distinct row."""
    display = PortForwardLiveDisplay(context=None)
    display.started(_make_snapshot("svc-a", pid=1))
    display.started(_make_snapshot("svc-b", pid=2))
    assert display._table.render().row_count == 2


def test_stopped_marks_row_as_stopped():
    """stopped() transitions the row status to stopped."""
    display = PortForwardLiveDisplay(context=None)
    snapshot = _make_snapshot("svc")
    display.started(snapshot)

    finished = PortForwardProcessSnapshot(
        namespace="ns",
        service_name="svc",
        remote_port=80,
        local_port=9000,
        pid=1234,
        returncode=0,
    )
    display.stopped(finished)

    cells = list(display._table.render().columns[-1].cells)
    assert "stopped" in str(cells[0])


def test_died_marks_row_as_died_with_exit_code():
    """died() transitions the row to died and includes the exit code."""
    display = PortForwardLiveDisplay(context=None)
    snapshot = _make_snapshot("svc")
    display.started(snapshot)

    finished = PortForwardProcessSnapshot(
        namespace="ns",
        service_name="svc",
        remote_port=80,
        local_port=9000,
        pid=1234,
        returncode=1,
    )
    display.died(finished)

    cells = list(display._table.render().columns[-1].cells)
    cell_text = str(cells[0])
    assert "died" in cell_text
    assert "1" in cell_text
