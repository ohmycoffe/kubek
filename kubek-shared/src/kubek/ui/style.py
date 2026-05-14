from questionary import Style

# Unified color palette for all Kubek projects
COLOR_ACCENT = "#e5c07b"  # yellow     — draws attention (qmark)
COLOR_SUCCESS = "#98c379"  # green      — confirmed / selected
COLOR_ACTIVE = "#61afef"  # blue       — navigation / pointer
COLOR_WARNING = "#d19a66"  # orange     — warnings / cautions
COLOR_ERROR = "#e06c75"  # red        — errors / failures
COLOR_MUTED = "#5c6370"  # gray       — secondary elements
COLOR_SUBTLE = "#4b5263"  # dark gray  — near-invisible hints

# Aliases for questionary compatibility
QMARK_COLOR = COLOR_ACCENT
ANSWER_COLOR = COLOR_SUCCESS
POINTER_COLOR = COLOR_ACTIVE
SELECTED_COLOR = COLOR_SUCCESS
SEPARATOR_COLOR = COLOR_SUBTLE
INSTRUCTION_COLOR = COLOR_SUBTLE
DISABLED_COLOR = COLOR_SUBTLE

# Questionary theme for interactive prompts
STYLE = Style(
    [
        ("qmark", f"fg:{QMARK_COLOR} bold"),
        ("question", "bold"),
        ("answer", f"fg:{ANSWER_COLOR} bold"),
        ("pointer", f"fg:{POINTER_COLOR} bold"),
        ("highlighted", f"fg:{POINTER_COLOR} bold"),
        ("selected", f"fg:{SELECTED_COLOR}"),
        ("separator", f"fg:{SEPARATOR_COLOR}"),
        ("instruction", f"fg:{INSTRUCTION_COLOR} italic"),
        ("text", ""),
        ("disabled", f"fg:{DISABLED_COLOR} italic"),
    ]
)
