from typing import Literal

import questionary
from kubek.kube import Kind
from kubek.term import DEFAULT_QUESTIONARY_THEME
from questionary import Style

QUESTIONARY_STYLE = Style(DEFAULT_QUESTIONARY_THEME)


def ask_for_kind() -> Literal[Kind.DEPLOYMENT, Kind.WORKFLOWTEMPLATE] | None:
    selected = questionary.select(
        "Select a kind:",
        choices=[
            questionary.Choice(
                title="Deployment",
                value=Kind.DEPLOYMENT,
                description="(Kubernetes Deployment)",
            ),
            questionary.Choice(
                title="WorkflowTemplate",
                value=Kind.WORKFLOWTEMPLATE,
                description="(Argo WorkflowTemplate)",
            ),
        ],
        use_jk_keys=False,
        style=QUESTIONARY_STYLE,
    ).ask()

    return selected


def ask_for_resource(resources: list[str], kind: Kind) -> str:
    selected = questionary.select(
        f"Select a {kind.value}:",
        choices=resources,
        use_search_filter=True,
        use_jk_keys=False,
        style=QUESTIONARY_STYLE,
    ).ask()

    return selected
