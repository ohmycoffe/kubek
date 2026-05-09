from questionary import Style

# fmt: off
COLOR_ACCENT  = "#e5c07b"  # yellow     — draws attention (qmark)
COLOR_SUCCESS = "#98c379"  # green      — confirmed / selected
COLOR_ACTIVE  = "#61afef"  # blue       — navigation / pointer
COLOR_WARNING  = "#d19a66"  # orange     — warnings / cautions
COLOR_ERROR   = "#e06c75"  # red        — errors / failures
COLOR_MUTED   = "#5c6370"  # gray       — secondary elements
COLOR_SUBTLE  = "#4b5263"  # dark gray  — near-invisible hints

# fmt: off
STYLE = Style(
    [
        ("qmark",       f"fg:{COLOR_ACCENT} bold"),
        ("question",    "bold"),
        ("answer",      f"fg:{COLOR_SUCCESS} bold"),
        ("pointer",     f"fg:{COLOR_ACTIVE} bold"),
        ("highlighted", f"fg:{COLOR_ACTIVE} bold"),
        ("selected",    f"fg:{COLOR_SUCCESS}"),
        ("separator",   f"fg:{COLOR_MUTED}"),
        ("instruction", f"fg:{COLOR_SUBTLE} italic"),
        ("text",        ""),
        ("disabled",    f"fg:{COLOR_SUBTLE} italic"),
    ]
)
# fmt: on
