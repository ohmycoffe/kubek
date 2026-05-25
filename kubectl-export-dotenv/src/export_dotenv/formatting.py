from __future__ import annotations

import datetime
import enum
import json


class ExportFormat(enum.StrEnum):
    ENV = "env"
    JSON = "json"


def export_as_dotenv(vals: dict[str, str], name: str | None) -> str:
    sorted_list = sorted(vals.items(), key=lambda x: x[0])
    res = []
    if name:
        now = datetime.datetime.now().isoformat(timespec="seconds")
        res.append(f"# {name} @ {now}")
    for key, value in sorted_list:
        res.append(f"{key}={value}")
    return "\n".join(res)


def format_environment_values(
    values: dict[str, str],
    output: ExportFormat,
    name: str | None = None,
) -> str:
    """Format environment values for output.

    This is a pure function:
    - no CLI
    - no printing
    - no Typer
    """

    if output == ExportFormat.JSON:
        return json.dumps(
            obj=values,
            sort_keys=True,
            indent=2,
        )

    if output == ExportFormat.ENV:
        return export_as_dotenv(
            vals=values,
            name=name,
        )
    # should never happen due to type system, but just in case
    raise AssertionError(f"Unsupported output format: {output}")
