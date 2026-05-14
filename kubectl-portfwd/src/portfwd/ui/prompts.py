from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, TypeAlias

import questionary
import typer
from kubek.ui import STYLE, console

from portfwd.config import GroupRef

if TYPE_CHECKING:
    from portfwd.kube import KubernetesService, RunningPortForward


class SpecialGroups(StrEnum):
    CUSTOM = "custom"


GroupNamesSelection: TypeAlias = GroupRef | SpecialGroups


def _service_sort_key(svc: KubernetesService) -> tuple[str, str, int]:
    return (svc.namespace, svc.name, svc.port)


def _get_title(service: KubernetesService) -> str:
    return f"{service.namespace}/{service.name}  :{service.port}  {service.protocol}"


def _get_key(service: KubernetesService) -> tuple[str, int]:
    return (service.name, service.port)


def build_service_choices(
    available_services: list[KubernetesService],
    running_port_forwards: list[RunningPortForward],
) -> list[questionary.Choice]:
    ports = {(r.name, r.remote_port): r.local_port for r in running_port_forwards}
    choices: list[questionary.Choice] = []

    for svc in sorted(
        [svc for svc in available_services if _get_key(svc) not in ports],
        key=_service_sort_key,
    ):
        choices.append(questionary.Choice(title=_get_title(svc), value=svc))

    for svc in sorted(
        [svc for svc in available_services if _get_key(svc) in ports],
        key=_service_sort_key,
    ):
        disabled = f"already forwarded → localhost:{ports[_get_key(svc)]}"
        choices.append(
            questionary.Choice(title=_get_title(svc), value=svc, disabled=disabled)
        )

    return choices


def select_namespaces(
    all_namespaces: list[str],
    current_namespace: str | None,
) -> list[str]:
    ordered = (
        [current_namespace] + [ns for ns in all_namespaces if ns != current_namespace]
        if current_namespace in all_namespaces
        else all_namespaces
    )
    choices = [
        questionary.Choice(
            title=f"{ns} (current namespace)" if ns == current_namespace else ns,
            value=ns,
            checked=(ns == current_namespace),
        )
        for ns in ordered
    ]
    selected: list[str] = questionary.checkbox(
        "Select namespaces:",
        choices=choices,
        use_search_filter=True,
        use_jk_keys=False,
        style=STYLE,
    ).ask()

    if not selected:
        console.print("[yellow]No namespaces selected. Exiting.[/yellow]")
        raise typer.Exit(code=0)
    return selected


def select_services(
    available_services: list[KubernetesService],
    running_port_forwards: list[RunningPortForward],
) -> list[KubernetesService]:
    choices = build_service_choices(available_services, running_port_forwards)
    selected: list[KubernetesService] = questionary.checkbox(
        "Select services to forward:",
        choices=choices,
        use_search_filter=True,
        use_jk_keys=False,
        style=STYLE,
    ).ask()
    if not selected:
        console.print("[yellow]No services selected. Exiting.[/yellow]")
        raise typer.Exit(code=0)
    return selected


def select_group_name(groups: list[GroupRef]) -> GroupNamesSelection:
    if not groups:
        return SpecialGroups.CUSTOM

    choices = [
        *(questionary.Choice(title=group.name, value=group) for group in groups),
        questionary.Choice(
            title="custom",
            value=SpecialGroups.CUSTOM,
            description="(interactive: select services to forward)",
        ),
    ]
    selected = questionary.select(
        "Select a group to run:",
        choices=choices,
        use_jk_keys=False,
        style=STYLE,
    ).ask()
    return selected
