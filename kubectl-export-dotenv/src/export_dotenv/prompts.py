from typing import Literal

import questionary
from kubek.kube import Kind
from kubek.term import DEFAULT_QUESTIONARY_THEME
from questionary import Style

QUESTIONARY_STYLE = Style(DEFAULT_QUESTIONARY_THEME)


def ask_for_kind() -> (
    Literal[
        Kind.DEPLOYMENT,
        Kind.STATEFULSET,
        Kind.DAEMONSET,
        Kind.REPLICASET,
        Kind.JOB,
        Kind.CRONJOB,
        Kind.WORKFLOWTEMPLATE,
        Kind.CONFIGMAP,
        Kind.SECRET,
        Kind.POD,
    ]
    | None
):
    selected = questionary.select(
        "Select a kind:",
        choices=[
            questionary.Choice(
                title="Deployment",
                value=Kind.DEPLOYMENT,
                description="(Kubernetes Deployment)",
            ),
            questionary.Choice(
                title="StatefulSet",
                value=Kind.STATEFULSET,
                description="(Kubernetes StatefulSet)",
            ),
            questionary.Choice(
                title="DaemonSet",
                value=Kind.DAEMONSET,
                description="(Kubernetes DaemonSet)",
            ),
            questionary.Choice(
                title="ReplicaSet",
                value=Kind.REPLICASET,
                description="(Kubernetes ReplicaSet)",
            ),
            questionary.Choice(
                title="Job",
                value=Kind.JOB,
                description="(Kubernetes Job)",
            ),
            questionary.Choice(
                title="CronJob",
                value=Kind.CRONJOB,
                description="(Kubernetes CronJob)",
            ),
            questionary.Choice(
                title="WorkflowTemplate",
                value=Kind.WORKFLOWTEMPLATE,
                description="(Argo WorkflowTemplate)",
            ),
            questionary.Choice(
                title="ConfigMap",
                value=Kind.CONFIGMAP,
                description="(Kubernetes ConfigMap)",
            ),
            questionary.Choice(
                title="Pod",
                value=Kind.POD,
                description="(Kubernetes Pod)",
            ),
            questionary.Choice(
                title="Secret",
                value=Kind.SECRET,
                description="(Kubernetes Secret)",
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
