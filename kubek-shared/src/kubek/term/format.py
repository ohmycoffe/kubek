import logging
from typing import TYPE_CHECKING

from rich.panel import Panel
from rich.style import Style
from rich.text import Text

from kubek.term.style import Color, Icon, RichStyle

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


LABEL_WIDTH = 8
ICON_WIDTH = 3  # reserve space for emoji column


def _fmt(
    msg: str,
    *,
    style: RichStyle | None = None,
    icon: str | None = None,
    label: str | None = None,
    indent: int = 0,
    style_msg: bool = False,
) -> Text:
    text = Text()

    # indent
    if indent:
        text.append(" " * indent)

    # icon
    if icon:
        text.append(f"{icon}".ljust(ICON_WIDTH))

    # label
    if label:
        text.append(f"{label:<{LABEL_WIDTH}}", style=style)

    # spacing between label and message
    if icon or label:
        text.append(" ")

    # message
    if isinstance(msg, Text):
        assert not style_msg, "If msg is a Text object, style_msg should be False"
        text.append_text(msg)
    else:
        text.append(msg, style=style if style_msg else None)

    return text


# --- main message types ---
def info(msg: str) -> Text:
    return _fmt(
        msg,
        label="Info",
        style=RichStyle.INFO,
        icon=Icon.INFO,
    )


# --- muted (secondary lines) ---
def mute(msg: str) -> Text:
    return _fmt(
        msg,
        style=RichStyle.MUTED,
        style_msg=True,
    )


def success(msg: str) -> Text:
    return _fmt(msg, label="Success", style=RichStyle.SUCCESS, icon=Icon.SUCCESS)


def warn(msg: str) -> Text:
    return _fmt(msg, label="Warning", style=RichStyle.WARNING, icon=Icon.WARNING)


def error(msg: str) -> Text:
    return _fmt(msg, label="Error", style=RichStyle.ERROR, icon=Icon.ERROR)


def ongoing_status(msg: str) -> Text:
    return _fmt(msg, style=RichStyle.ONGOING_STATUS, style_msg=True)


# --- fatal (strong visual separation) ---
def fatal(msg: str) -> Panel:
    return Panel(
        msg,
        title=Text(f"{Icon.FATAL} FATAL ERROR", style=RichStyle.ERROR),
        border_style=Color.ERROR,
        expand=False,
    )


def highlight(msg: str) -> Text:
    return Text(msg, style=Style(color="cyan"))


if __name__ == "__main__":
    from kubek.term.console import get_console

    # Run this as a script to see the formatting examples
    console = get_console()
    console.print("This is normal message")
    console.print("This is", highlight("highlighted"), "message")
    console.print(ongoing_status("This is an ongoing message."))
    console.print(mute("This is a muted message."))
    console.print(info("This is a status message."))
    console.print(success("This is a success message."))
    console.print(warn("This is a warning message."))
    console.print(error("This is an error message."))
    console.print(fatal("This is another fatal error message."))
