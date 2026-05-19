from enum import StrEnum

import questionary
from rich.style import Style
from rich.theme import Theme

# fmt:off

# Colors
class Color(StrEnum):
    ACCENT  = "#e5c07b"  # draws attention (qmark)
    ERROR   = "#e06c75"  # errors / failures
    MUTED   = "#5c6370"  # secondary elements: side info, less important text
    STATUS  = "#61afef"  # status / step / activity / navigation
    SUBTLE  = "#4b5263"  # near-invisible hints: separators, disabled items
    SUCCESS = "#98c379"  # confirmed / selected
    WARNING = "#d19a66"  # warnings / cautions
    HIGHLIGHT = "cyan"  # for highlighting important info


class Icon(StrEnum):
    ERROR   = "❌"
    FATAL   = "🛑 "
    INFO  = "🟦"
    SUCCESS = "✅"
    WARNING = "⚠️   "


# Questionary theme for interactive prompts
STYLE_QUESTIONARY = questionary.Style(
    [
        ("qmark", f"fg:{Color.ACCENT} bold"),
        ("question", "bold"),
        ("answer", f"fg:{Color.SUCCESS} bold"),
        ("pointer", f"fg:{Color.STATUS} bold"),
        ("highlighted", f"fg:{Color.STATUS} bold"),
        ("selected", f"fg:{Color.SUCCESS}"),
        ("separator", f"fg:{Color.SUBTLE}"),
        ("instruction", f"fg:{Color.SUBTLE} italic"),
        ("text", ""),
        ("disabled", f"fg:{Color.SUBTLE} italic"),
    ]
)


class RichStyle(StrEnum):
    MUTED = "muted"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"
    HIGHLIGHT = "highlight"
    ONGOING_STATUS = "ongoing_status"


RICH_THEME = Theme(
    {
        RichStyle.MUTED: Style(color=Color.MUTED, italic=True),
        RichStyle.ERROR: Style(color=Color.ERROR, bold=True),
        RichStyle.WARNING: Style(color=Color.WARNING, bold=True),
        RichStyle.INFO: Style(color=Color.STATUS, bold=True),
        RichStyle.SUCCESS: Style(color=Color.SUCCESS, bold=True),
        RichStyle.HIGHLIGHT: Style(color=Color.HIGHLIGHT),
        RichStyle.ONGOING_STATUS: Style(
            dim=True,
            italic=True,
            bold=True,
            color=Color.STATUS,
        ),
    }
)
