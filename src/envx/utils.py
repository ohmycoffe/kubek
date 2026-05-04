from __future__ import annotations

import base64

import questionary
import typer


def decode(val: str) -> str:
    decoded_bytes = base64.b64decode(val)
    return decoded_bytes.decode("utf-8")


def export_as_dotenv(vals: dict[str, str], service_name: str | None = None) -> str:
    sorted_list = sorted(vals.items(), key=lambda x: x[0])
    res = []
    if service_name:
        res.append(f"# {service_name}")
    for key, value in sorted_list:
        res.append(f"{key}={value}")
    return "\n".join(res)


def resolve_namespace(value: str | None, available_namespaces: list[str]) -> str:
    if value:
        if value not in available_namespaces:
            typer.echo(f"Namespace '{value}' not found.", err=True)
            raise typer.Exit(code=1)
        return value
    selected = questionary.select(
        "Select a namespace:",
        choices=available_namespaces,
        use_search_filter=True,
        use_jk_keys=False,
    ).ask()
    if not selected:
        raise typer.Exit(code=0)
    return selected
