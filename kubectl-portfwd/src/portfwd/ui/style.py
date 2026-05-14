from questionary import Style

QMARK_COLOR = "#61afef"
ANSWER_COLOR = "#98c379"
POINTER_COLOR = "#61afef"
SELECTED_COLOR = "#98c379"
SEPARATOR_COLOR = "#4b5263"
INSTRUCTION_COLOR = "#4b5263"
DISABLED_COLOR = "#4b5263"

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
