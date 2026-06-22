from __future__ import annotations

import questionary
from kubek.term import DEFAULT_QUESTIONARY_THEME

from portfwd.domain.models import PortForwardSpec, TargetKind

QUESTIONARY_STYLE = questionary.Style(DEFAULT_QUESTIONARY_THEME)


def ask_for_kinds() -> list[TargetKind]:
    """Prompt the user to pick which resource types to forward."""
    choices = [
        questionary.Choice(
            title="Services",
            value=TargetKind.SERVICE,
            checked=True,
        ),
        questionary.Choice(
            title="Pods",
            value=TargetKind.POD,
        ),
        questionary.Choice(
            title="Deployments",
            value=TargetKind.DEPLOYMENT,
        ),
        questionary.Choice(
            title="StatefulSets",
            value=TargetKind.STATEFULSET,
        ),
        questionary.Choice(
            title="DaemonSets",
            value=TargetKind.DAEMONSET,
        ),
        questionary.Choice(
            title="ReplicaSets",
            value=TargetKind.REPLICASET,
        ),
    ]
    return questionary.checkbox(
        "Select resource types to forward:",
        choices=choices,
        initial_choice=TargetKind.SERVICE,
        use_jk_keys=False,
        style=QUESTIONARY_STYLE,
    ).ask()


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


def _target_choice_title(spec: PortForwardSpec) -> str:
    base = f"{spec.target.kind}/{spec.target.namespace}/{spec.target.name}"
    if spec.remote_port is None:
        return f"{base}  (specify :port)"
    return f"{base}  :{spec.remote_port}"


def ask_for_targets(
    available_targets: list[PortForwardSpec],
) -> list[PortForwardSpec]:
    """Prompt the user to pick services and pods to forward from a sorted list."""
    choices = [
        questionary.Choice(
            title=_target_choice_title(t),
            value=t,
        )
        for t in sorted(
            available_targets,
            key=lambda t: (
                t.target.kind,
                t.target.namespace,
                t.target.name,
                t.remote_port if t.remote_port is not None else -1,
            ),
        )
    ]
    return questionary.checkbox(
        "Select targets to forward:",
        choices=choices,
        use_search_filter=True,
        use_jk_keys=False,
        style=QUESTIONARY_STYLE,
    ).ask()
