from __future__ import annotations

from typing import TypeAlias

import questionary
from kubek.term import DEFAULT_QUESTIONARY_THEME

from portfwd.domain.config import GroupSpec, SpecialGroups
from portfwd.domain.models import ServicePortForwardSpec

GroupNamesSelection: TypeAlias = GroupSpec | SpecialGroups

QUESTIONARY_STYLE = questionary.Style(DEFAULT_QUESTIONARY_THEME)


def ask_for_namespace(
    all_namespaces: list[str],
    current_namespace: str | None,
) -> list[str]:
    """Prompt the user to pick one or more namespaces."""
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
    return questionary.checkbox(
        "Select namespaces:",
        choices=choices,
        use_search_filter=True,
        use_jk_keys=False,
        style=QUESTIONARY_STYLE,
    ).ask()


def ask_for_service(
    available_services: list[ServicePortForwardSpec],
) -> list[ServicePortForwardSpec]:
    """Prompt the user to pick services to forward from a sorted list."""
    choices = [
        questionary.Choice(
            title=f"{s.target.namespace}/{s.target.name}  :{s.remote_port}",
            value=s,
        )
        for s in sorted(
            available_services,
            key=lambda x: (x.target.namespace, x.target.name, x.remote_port),
        )
    ]
    return questionary.checkbox(
        "Select services to forward:",
        choices=choices,
        use_search_filter=True,
        use_jk_keys=False,
        style=QUESTIONARY_STYLE,
    ).ask()


def ask_for_group(groups: list[GroupSpec]) -> GroupNamesSelection:
    """Prompt the user to pick a group, or fall back to the interactive flow."""
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
    return questionary.select(
        "Select a group to run:",
        choices=choices,
        use_jk_keys=False,
        style=QUESTIONARY_STYLE,
    ).ask()
