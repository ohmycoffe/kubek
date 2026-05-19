from __future__ import annotations

import enum
import json
import subprocess
from pathlib import Path
from typing import Annotated

import kubek.term.format as fmt
import questionary
import typer
from click import BadParameter
from kubek.kube import DEFAULT_NAMESPACE
from kubek.kube.client import (
    ContextNotSetError,
    KubectlError,
    KubectlWrapper,
)
from kubek.term import STYLE_QUESTIONARY, get_console, print_error

from export_dotenv.kube import (
    get_deployment_envs,
    get_workflowtemplate_envs,
)
from export_dotenv.utils import export_as_dotenv, setup_logging

console = get_console()


class KindOptions(enum.StrEnum):
    DEPLOYMENT = "deployment"
    WORKFLOWTEMPLATE = "workflowtemplate"


class ExportFormat(enum.StrEnum):
    ENV = "env"
    JSON = "json"


app = typer.Typer()


def ask_for_kind() -> KindOptions:
    selected = questionary.select(
        "Select a kind:",
        choices=[
            questionary.Choice(
                title="Deployment",
                value=KindOptions.DEPLOYMENT,
                description="(Kubernetes Deployment)",
            ),
            questionary.Choice(
                title="WorkflowTemplate",
                value=KindOptions.WORKFLOWTEMPLATE,
                description="(Argo WorkflowTemplate)",
            ),
        ],
        use_jk_keys=False,
        style=STYLE_QUESTIONARY,
    ).ask()

    return KindOptions(selected)


def ask_for_resource(resources: list[str], kind: KindOptions) -> str:
    selected = questionary.select(
        f"Select a {kind.value}:",
        choices=resources,
        use_search_filter=True,
        use_jk_keys=False,
        style=STYLE_QUESTIONARY,
    ).ask()
    return selected


@app.callback(invoke_without_command=True)
def get(
    kind: Annotated[
        KindOptions | None,
        typer.Option(
            help="Kind of resource to get parameters for. If not provided, you will be prompted to select one.",
        ),
    ] = None,
    context: Annotated[
        str | None,
        typer.Option(
            help="Kubernetes context. If not provided, the current context will be used.",
        ),
    ] = None,
    kubeconfig: Annotated[
        Path | None,
        typer.Option(
            "--kubeconfig",
            exists=True,
            file_okay=True,
            dir_okay=False,
            resolve_path=True,
            help="Path to a kubeconfig file (single path). Omit to use kubectl's default.",
        ),
    ] = None,
    namespace: Annotated[
        str | None,
        typer.Option(
            help="Kubernetes namespace. If not provided, you will be prompted to select one.",
        ),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option(
            help="Name of the resource. If not provided, you will be prompted to select one.",
        ),
    ] = None,
    output: ExportFormat = ExportFormat.ENV,
    verbose: Annotated[
        int,
        typer.Option(
            "--verbose", "-v", count=True, help="Verbose output. Use -vv for debug."
        ),
    ] = 0,
):
    """
    Get environment variables for a Kubernetes deployment or Argo WorkflowTemplate.
    """
    setup_logging(verbose)

    kubeconfig_path = str(kubeconfig) if kubeconfig is not None else None
    if kubeconfig_path:
        console.print("Kubeconfig:", fmt.highlight(kubeconfig_path))

    try:
        kube_config = KubectlWrapper.get_config(
            kubeconfig=kubeconfig_path, context=context
        )
    except ContextNotSetError as e:
        print_error(e, "Failed to get current context from kubeconfig")
        raise typer.Exit(code=1) from None

    context = context or kube_config.current_context
    if context is None:
        console.print(
            fmt.error(
                "No active context found in kubeconfig. Please specify a context using the '--context' flag or set a current context in your kubeconfig."
            )
        )
        raise typer.Exit(code=1) from None

    console.print("Context:", fmt.highlight(context))

    namespace = namespace or kube_config.current_namespace or DEFAULT_NAMESPACE
    console.print("Namespace:", fmt.highlight(namespace))

    kind = kind or ask_for_kind()

    if not kind:
        raise typer.Exit(code=0)

    kubectl = KubectlWrapper(
        namespace=namespace, context=context, kubeconfig=kubeconfig_path
    )

    try:
        with console.status(
            fmt.ongoing_status(f"Fetching available {kind.value}s in {namespace}…")
        ):
            if kind == KindOptions.DEPLOYMENT:
                resources = kubectl.get_deployments()
            else:
                resources = kubectl.get_workflowtemplates()
    except KubectlError as e:
        print_error(
            e, f"Failed to fetch available {kind.value}s in namespace '{namespace}'"
        )
        raise typer.Exit(code=1) from None
    if not resources:
        console.print(fmt.error(f"No {kind.value}s found in namespace '{namespace}'"))
        raise typer.Exit(code=1)

    available_names = [r.metadata.name for r in resources]
    if not name:
        name = ask_for_resource(resources=available_names, kind=kind)
        if not name:
            raise typer.Exit(code=0)

    if name not in available_names:
        console.print(
            fmt.error(f"{kind.value} '{name}' not found in namespace '{namespace}'")
        )
        raise typer.Exit(code=1)

    try:
        with console.status(fmt.ongoing_status("Fetching environment variables…")):
            if kind == KindOptions.DEPLOYMENT:
                vals = get_deployment_envs(name=name, kubectl=kubectl)
            elif kind == KindOptions.WORKFLOWTEMPLATE:
                vals = get_workflowtemplate_envs(name=name, kubectl=kubectl)
            else:
                raise BadParameter(f"Unsupported kind: {kind}")
    except subprocess.CalledProcessError as e:
        print_error(e, f"Failed to fetch environment variables for '{name}'")
        raise typer.Exit(code=1) from None

    if output == ExportFormat.JSON:
        formatted = json.dumps(vals, sort_keys=True)
    elif output == ExportFormat.ENV:
        formatted = export_as_dotenv(vals=vals, name=name)
    print(formatted)
    raise typer.Exit(code=0)
