from dataclasses import dataclass
from enum import StrEnum

from rich.style import Style

# fmt:off

# Colors
class Color(StrEnum):
    # semantic states
    ERROR   = "#e06c75"  # errors / failures
    SUCCESS = "#98c379"  # confirmed / selected
    WARNING = "#d19a66"  # warnings / cautions
    # activity states
    ONGOING  = "#61afef"  # status / step / activity / navigation
    # hierarchy / emphasis
    MUTED   = "#5c6370"  # secondary elements: side info, less important text
    SUBTLE  = "#4b5263"  # near-invisible hints: separators, disabled items
    # highlighting
    HIGHLIGHT = "cyan"  # for highlighting important info

@dataclass(frozen=True)
class PrefixSpec:
    style: Style | None = None
    msg: str = ""

@dataclass(frozen=True)
class MessageSpec:
    message_style: Style | None = None
    prefix: PrefixSpec | None = None
    highlight_style: Style  = Style(color=Color.HIGHLIGHT)


@dataclass(frozen=True)
class MessageStyles:
    info: MessageSpec
    success: MessageSpec
    warning: MessageSpec
    error: MessageSpec
    muted: MessageSpec
    ongoing: MessageSpec


# Questionary theme for interactive prompts
DEFAULT_QUESTIONARY_THEME = [
    ("qmark", f"fg:{Color.HIGHLIGHT} bold"),
    ("question", "bold"),
    ("answer", f"fg:{Color.SUCCESS} bold"),
    ("pointer", f"fg:{Color.ONGOING} bold"),
    ("highlighted", f"fg:{Color.ONGOING} bold"),
    ("selected", f"fg:{Color.SUCCESS}"),
    ("separator", f"fg:{Color.SUBTLE}"),
    ("instruction", f"fg:{Color.SUBTLE} italic"),
    ("text", ""),
    ("disabled", f"fg:{Color.SUBTLE} italic")
]

class Icon(StrEnum):
    ERROR   = "❌"
    FATAL   = "🛑 "
    INFO  = "🟦"
    SUCCESS = "✅"
    WARNING = "⚠️   "


DEFAULT_MESSAGE_STYLES = MessageStyles(
    # info=MessageSpec(
    #     message_style=Style(color=Color.ONGOING, bold=True),
    #     prefix=PrefixSpec(msg="🟦 "),
    # ),
    info=MessageSpec(),
    success=MessageSpec(
        message_style=Style(color=Color.SUCCESS, bold=True),
        prefix=PrefixSpec(msg="✅ "),
    ),
    warning=MessageSpec(
        message_style=Style(color=Color.WARNING, bold=True),
        prefix=PrefixSpec(msg="⚠️  "),
    ),
    error=MessageSpec(
        message_style=Style(color=Color.ERROR, bold=True),
        prefix=PrefixSpec(msg="❌ "),
    ),
    muted=MessageSpec(
        message_style=Style(color=Color.MUTED, italic=True),
    ),
    ongoing=MessageSpec(
        message_style=Style(
            dim=True,
            italic=True,
            bold=True,
            color=Color.ONGOING,
        ),
    )

)
