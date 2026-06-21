from pathlib import Path

import pytest
from portfwd.domain.errors import EmptySpecFileError, SpecFileLoadError
from portfwd.infrastructure.spec_file_loader import SpecFileLine, load_spec_file
from portfwd.presentation.cli import _load_spec_file


def test_load_spec_file_returns_service_lines(tmp_path: Path):
    spec_file = tmp_path / ".portfwd-plan"
    spec_file.write_text(
        "ns-kubectl-portfwd/httpd:8080::50000\nns-kubectl-portfwd/nginx:80::50001\n",
        encoding="utf-8",
    )

    assert load_spec_file(spec_file) == [
        SpecFileLine(1, "ns-kubectl-portfwd/httpd:8080::50000"),
        SpecFileLine(2, "ns-kubectl-portfwd/nginx:80::50001"),
    ]


def test_load_spec_file_skips_blank_lines_and_comments(tmp_path: Path):
    spec_file = tmp_path / "forwards"
    spec_file.write_text(
        "# backend services\n\ndefault/api:80::8080\n  # another comment\n",
        encoding="utf-8",
    )

    assert load_spec_file(spec_file) == [SpecFileLine(3, "default/api:80::8080")]


def test_load_spec_file_preserves_file_line_numbers(tmp_path: Path):
    spec_file = tmp_path / "forwards"
    spec_file.write_text(
        "# header\n\ndefault/api:80::8080\ndefault/bad:\n",
        encoding="utf-8",
    )

    assert load_spec_file(spec_file) == [
        SpecFileLine(3, "default/api:80::8080"),
        SpecFileLine(4, "default/bad:"),
    ]


def test_load_spec_file_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_spec_file(tmp_path / "missing")


def test_load_spec_file_empty_file_raises(tmp_path: Path):
    spec_file = tmp_path / "forwards"
    spec_file.write_text("# only comments\n\n", encoding="utf-8")

    with pytest.raises(EmptySpecFileError, match="no targets"):
        _load_spec_file(spec_file)


def test_load_spec_file_invalid_line_error_message(tmp_path: Path, monkeypatch):
    spec_file = tmp_path / ".portfwd-spec"
    spec_file.write_text(
        "ns-kubectl-portfwd/svc/httpd:8080::50000\n"
        "ns-kubectl-portfwd/svc/nginx:80:50001\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SpecFileLoadError) as exc_info:
        _load_spec_file(spec_file)

    assert str(exc_info.value) == (
        "invalid spec in .portfwd-spec at line 2: "
        '"ns-kubectl-portfwd/svc/nginx:80:50001"; '
        "expected [namespace/][type/]name[:remote_port][::local_port] (type: pod | service | deployment | statefulset); "
        "example ns-kubectl-portfwd/pod/nginx:80::50001"
    )
