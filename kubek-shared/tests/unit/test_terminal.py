"""Tests for CLIOutput verbosity gating behaviour."""

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
from kubek.term.formatter import MessageFormatter
from kubek.term.output import CLIOutput
from kubek.term.style import DEFAULT_MESSAGE_STYLES
from kubek.term.verbosity import Verbosity, VerbosityLevel
from rich.console import Console


def _make_output(verbosity_count: int) -> tuple[CLIOutput, MagicMock]:
    console = MagicMock(spec=Console)
    formatter = MessageFormatter(styles=DEFAULT_MESSAGE_STYLES)
    verbosity = Verbosity.from_count(verbosity_count)
    output = CLIOutput(console=console, formatter=formatter, verbosity=verbosity)
    return output, console


@pytest.mark.parametrize(
    "method_name,message",
    [
        ("note", "hello"),
        ("success", "done"),
        ("caution", "careful"),
        ("problem", "oops"),
    ],
)
def test_normal_level_messages_print_at_normal_verbosity(
    method_name: str,
    message: str,
) -> None:
    output, console = _make_output(0)

    method: Callable[[str], None] = getattr(output, method_name)
    method(message)

    console.print.assert_called_once()


@pytest.mark.parametrize(
    "verbosity_count,should_print",
    [
        (0, False),
        (1, True),
        (2, True),
    ],
)
def test_detail_uses_verbose_gate(
    verbosity_count: int,
    should_print: bool,
) -> None:
    output, console = _make_output(verbosity_count)

    output.detail("extra info")

    if should_print:
        console.print.assert_called_once()
    else:
        console.print.assert_not_called()


@pytest.mark.parametrize(
    "verbosity_count,should_print",
    [
        (0, False),
        (1, False),
        (2, True),
    ],
)
def test_diagnostic_uses_diagnostic_gate(
    verbosity_count: int,
    should_print: bool,
) -> None:
    output, console = _make_output(verbosity_count)

    output.diagnostic("debug info")

    if should_print:
        console.print.assert_called_once()
    else:
        console.print.assert_not_called()


@pytest.mark.parametrize(
    "verbosity_count,should_print_traceback",
    [
        (0, False),
        (1, False),
        (2, True),
    ],
)
def test_exception_always_prints_problem_but_traceback_only_at_diagnostic(
    verbosity_count: int,
    should_print_traceback: bool,
) -> None:
    output, console = _make_output(verbosity_count)

    output.exception("something went wrong")

    console.print.assert_called_once()

    if should_print_traceback:
        console.print_exception.assert_called_once()
    else:
        console.print_exception.assert_not_called()


@pytest.mark.parametrize(
    "count,expected_level",
    [
        (0, VerbosityLevel.NORMAL),
        (-3, VerbosityLevel.NORMAL),
        (1, VerbosityLevel.VERBOSE),
        (2, VerbosityLevel.DIAGNOSTIC),
        (3, VerbosityLevel.DIAGNOSTIC),
        (10, VerbosityLevel.DIAGNOSTIC),
    ],
)
def test_from_count_resolves_level(
    count: int,
    expected_level: VerbosityLevel,
) -> None:
    assert Verbosity.from_count(count).level == expected_level


@pytest.mark.parametrize(
    "verbosity_count,required_level,expected",
    [
        (0, VerbosityLevel.NORMAL, True),
        (0, VerbosityLevel.VERBOSE, False),
        (0, VerbosityLevel.DIAGNOSTIC, False),
        (1, VerbosityLevel.NORMAL, True),
        (1, VerbosityLevel.VERBOSE, True),
        (1, VerbosityLevel.DIAGNOSTIC, False),
        (2, VerbosityLevel.NORMAL, True),
        (2, VerbosityLevel.VERBOSE, True),
        (2, VerbosityLevel.DIAGNOSTIC, True),
    ],
)
def test_allows_uses_verbosity_level_gate(
    verbosity_count: int,
    required_level: VerbosityLevel,
    expected: bool,
) -> None:
    verbosity = Verbosity.from_count(verbosity_count)

    assert verbosity.allows(required_level) is expected


@pytest.mark.parametrize(
    "count,expected",
    [
        (0, False),
        (1, False),
        (2, True),
        (3, True),
    ],
)
def test_show_tracebacks_only_for_diagnostic(
    count: int,
    expected: bool,
) -> None:
    assert Verbosity.from_count(count).show_tracebacks is expected
