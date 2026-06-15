from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import typer
from kubek.kube import (
    Kind,
    KubeClientError,
    KubeConfig,
    KubeFacade,
    ResolvedKubeConfig,
)
from kubek.term import CLIOutput, create_output, setup_logging_from_count

from export_dotenv.errors import (
    ExportDotenvError,
    NoResourcesFoundError,
)
from export_dotenv.formatting import ExportFormat, format_environment_values
from export_dotenv.kube import KubeGateway
from export_dotenv.prompts import ask_for_kind, ask_for_resource
from export_dotenv.use_case import fetch_environment_values

app = typer.Typer()


@app.callback(invoke_without_command=True)
def get(
    kind: Annotated[
        Literal[Kind.DEPLOYMENT, Kind.WORKFLOWTEMPLATE] | None,
        typer.Option(
            case_sensitive=False,
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
    setup_logging_from_count(verbose, "kubek", "export-dotenv")
    out: CLIOutput = create_output(verbosity_count=verbose)

    kubeconfig_str = kubeconfig if kubeconfig else None

    try:
        kube_config = KubeConfig(
            context=context,
            namespace=namespace,
            kubeconfig=kubeconfig_str,
        )

        api = KubeFacade.from_config(config=kube_config)
        _print_kubeconfig(out, api.current_config)

        selected_kind = kind or ask_for_kind()  # type: ignore
        if not selected_kind:
            raise typer.Exit(code=0)

        selected_name = name or _select_resource_name(
            out=out,
            kind=selected_kind,
            api=api,
        )

        if not selected_name:
            raise typer.Exit(code=0)

        with out.progress("Fetching environment variables…"):
            values = fetch_environment_values(
                kind=selected_kind,
                name=selected_name,
                api=api,
            )

        formatted = format_environment_values(
            values=values,
            name=selected_name,
            output=output,
        )
    except (ExportDotenvError, KubeClientError) as e:
        out.exception(str(e))
        raise typer.Exit(code=1) from None

    except Exception:
        out.exception("An unexpected error occurred. Use -vv for more details.")
        raise typer.Exit(code=1) from None

    typer.echo(formatted)
    raise typer.Exit(code=0)


def _print_kubeconfig(out: CLIOutput, kube_config: ResolvedKubeConfig) -> None:
    if kube_config.kubeconfig:
        out.note(
            f"Kubeconfig: {kube_config.kubeconfig}",
            highlight=[str(kube_config.kubeconfig)],
        )

    if kube_config.context:
        out.note(
            f"Context: {kube_config.context}",
            highlight=[str(kube_config.context)],
        )

    if kube_config.namespace:
        out.note(
            f"Namespace: {kube_config.namespace}",
            highlight=[str(kube_config.namespace)],
        )


def _select_resource_name(
    out: CLIOutput,
    kind: Kind,
    api: KubeGateway,
) -> str:
    with out.progress(
        f"Fetching available {kind.value}s in {api.current_config.namespace}…"
    ):
        if kind == Kind.DEPLOYMENT:
            resources = api.deployment.list()
        else:
            resources = api.workflowtemplate.list()

    if not resources:
        raise NoResourcesFoundError(
            f"No {kind.value}s found in namespace '{api.current_config.namespace}'"
        )

    available_names = [r.metadata.name for r in resources]
    name = ask_for_resource(resources=available_names, kind=kind)
    return name
