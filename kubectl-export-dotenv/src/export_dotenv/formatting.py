from __future__ import annotations

import datetime
import enum
import json
from dataclasses import asdict

from export_dotenv.kube.env_fetchers import EnvironmentValues


class ExportFormat(enum.StrEnum):
    ENV = "env"
    JSON = "json"


def export_as_dotenv(vals: list[EnvironmentValues], name: str | None) -> str:
    res = []
    if name:
        now = datetime.datetime.now().isoformat(timespec="seconds")
        res.append(f"# {name} @ {now}")
    for container_envs in vals:
        if len(vals) > 1:
            res.append(f"# container: {container_envs.name}")
        sorted_list = sorted(container_envs.values.items(), key=lambda x: x[0])
        for key, value in sorted_list:
            res.append(f"{key}={value}")
    return "\n".join(res)


def format_environment_values(
    values: list[EnvironmentValues],
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
            obj=[asdict(val) for val in values],
            sort_keys=True,
            indent=2,
            default=str,
        )

    if output == ExportFormat.ENV:
        return export_as_dotenv(
            vals=values,
            name=name,
        )
    # should never happen due to type system, but just in case
    raise AssertionError(f"Unsupported output format: {output}")
