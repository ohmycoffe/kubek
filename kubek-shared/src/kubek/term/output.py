from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from rich.console import Console

from kubek.term.formatter import MessageFormatter
from kubek.term.style import DEFAULT_MESSAGE_STYLES, MessageStyles
from kubek.term.verbosity import Verbosity, VerbosityLevel


class CLIOutput:
    """User-facing CLI messaging API.

    Responsibilities:
    - applies verbosity rules,
    - formats semantic messages,
    - sends formatted messages to the terminal.

    It intentionally avoids logging-style names like info/warn/error/debug.
    """

    def __init__(
        self, console: Console, formatter: MessageFormatter, verbosity: Verbosity
    ) -> None:
        self.__console = console
        self.__formatter = formatter
        self.__verbosity = verbosity

    @property
    def console(self) -> Console:
        """The Rich console used for all terminal output."""
        return self.__console

    def note(self, message: str, highlight: list[str] | None = None) -> None:
        """Show a normal informational user-facing message."""
        if not self.__verbosity.allows(VerbosityLevel.NORMAL):
            return

        self.__console.print(self.__formatter.note(message, highlight=highlight))

    def success(self, message: str, highlight: list[str] | None = None) -> None:
        """Show a successful outcome message."""
        if not self.__verbosity.allows(VerbosityLevel.NORMAL):
            return

        self.__console.print(self.__formatter.success(message, highlight=highlight))

    def caution(self, message: str, highlight: list[str] | None = None) -> None:
        """Show a user-facing caution/warning message."""
        if not self.__verbosity.allows(VerbosityLevel.NORMAL):
            return

        self.__console.print(self.__formatter.caution(message, highlight=highlight))

    def problem(self, message: str, highlight: list[str] | None = None) -> None:
        """Show a user-facing problem/failure message."""
        if not self.__verbosity.allows(VerbosityLevel.NORMAL):
            return

        self.__console.print(self.__formatter.problem(message, highlight=highlight))

    def detail(self, message: str, highlight: list[str] | None = None) -> None:
        """Show extra detail when verbose output is enabled."""
        if not self.__verbosity.allows(VerbosityLevel.VERBOSE):
            return

        self.__console.print(self.__formatter.muted(message, highlight=highlight))

    def diagnostic(self, message: str, highlight: list[str] | None = None) -> None:
        """Show diagnostic detail when diagnostic output is enabled."""
        if not self.__verbosity.allows(VerbosityLevel.DIAGNOSTIC):
            return

        self.__console.print(self.__formatter.muted(message, highlight=highlight))

    @contextmanager
    def progress(
        self,
        message: str,
        highlight: list[str] | None = None,
        *,
        verbosity: VerbosityLevel = VerbosityLevel.NORMAL,
    ) -> Iterator[None]:
        """Show a spinner-style progress message if allowed by verbosity."""
        if not self.__verbosity.allows(verbosity):
            yield
            return

        formatted = self.__formatter.ongoing(message, highlight=highlight)

        with self.__console.status(formatted):
            yield

    def exception(
        self,
        message: str,
        highlight: list[str] | None = None,
    ) -> None:
        """Show a clean error message and, in diagnostic mode, a traceback."""
        self.problem(message, highlight=highlight)

        if self.__verbosity.show_tracebacks:
            self.__console.print_exception()


def create_output(
    stderr: bool = True,
    styles: MessageStyles = DEFAULT_MESSAGE_STYLES,
    verbosity_count: int = VerbosityLevel.NORMAL.value,
) -> CLIOutput:
    return CLIOutput(
        verbosity=Verbosity.from_count(verbosity_count),
        console=Console(stderr=stderr),
        formatter=MessageFormatter(styles=styles),
    )


if __name__ == "__main__":
    messenger = create_output(verbosity_count=2)  # Show all messages and tracebacks

    messenger.note("This is a note")
    messenger.success("This is a success message")
    messenger.caution("This is a caution message")
    messenger.problem("This is a problem message")
    messenger.detail("This is a detail message")
    messenger.diagnostic("This is a diagnostic message", highlight=["diagnostic"])
    try:
        raise ValueError("Something went wrong!")
    except Exception:
        messenger.exception("An error occurred")

    with messenger.progress("Doing something..."):
        import time

        time.sleep(6)
