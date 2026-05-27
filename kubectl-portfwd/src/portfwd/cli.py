from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer
from kubek.kube import KubeConfig, KubeFacade
from kubek.kube.config import ResolvedKubeConfig
from kubek.kube.errors import KubeClientError
from kubek.term import create_output, setup_logging_from_count
from kubek.term.output import CLIOutput
from pydantic import ValidationError

from portfwd.config import DEFAULT_CONFIG_PATH, load_config
from portfwd.domain.errors import ConfigLoadError, PortForwardError
from portfwd.use_case import run_port_forwards

logger = logging.getLogger(__name__)

app = typer.Typer()


@app.callback(invoke_without_command=True)
def port_forward(
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            envvar="KUBEK_PORTFWD_CONFIG",
            help=f"Path to config file. Defaults to {DEFAULT_CONFIG_PATH}.",
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
    group: Annotated[
        str | None,
        typer.Option(
            "--group",
            "-g",
            help="Run a predefined service group from the config.",
        ),
    ] = None,
    service: Annotated[
        list[str] | None,
        typer.Option(
            "--service",
            "-s",
            help=(
                'Service to forward as "[namespace/]name[:remote_port][::local_port]". '
                "Can be specified multiple times."
            ),
        ),
    ] = None,
    verbose: Annotated[
        int,
        typer.Option(
            "--verbose",
            "-v",
            count=True,
            help="Verbose output. Use -vv for more detail.",
        ),
    ] = 0,
) -> None:
    """Interactive kubectl port-forward for Kubernetes services.

    \b
    Examples:
        kubectl portfwd
        kubectl portfwd -g backend
        kubectl portfwd -s kube-public/auth-service
        kubectl portfwd -s kube-public/auth-service:8080
        kubectl portfwd -s kube-public/auth-service:8080::50000
        kubectl portfwd -s kube-public/auth -s kube-public/api
    """
    setup_logging_from_count(verbose, "kubek", "portfwd")
    out: CLIOutput = create_output(verbosity_count=verbose)

    if group is not None and service is not None:
        raise typer.BadParameter("'--group' and '--service' are mutually exclusive.")

    kubeconfig_str = str(kubeconfig) if kubeconfig else None

    try:
        kube_config = KubeConfig(context=context, kubeconfig=kubeconfig_str)
        api = KubeFacade.from_config(config=kube_config)
        _print_kubeconfig(out, api.current_config)

        cfg = _load_config(config)

        run_port_forwards(
            cfg=cfg,
            group=group,
            service=service,
            api=api,
            out=out,
        )
    except (PortForwardError, KubeClientError) as e:
        out.exception(str(e))
        raise typer.Exit(code=1) from None
    except Exception:
        out.exception("An unexpected error occurred. Use -vv for more details.")
        raise typer.Exit(code=1) from None


def _load_config(path: Path | None):
    try:
        return load_config(path)
    except FileNotFoundError as e:
        raise ConfigLoadError(f"config file not found: {e.filename}") from e
    except ValidationError as e:
        raise ConfigLoadError(f"invalid configuration: {e}") from e
    except ValueError as e:
        raise ConfigLoadError(f"could not load configuration: {e}") from e


def _print_kubeconfig(out: CLIOutput, kube_config: ResolvedKubeConfig) -> None:
    if kube_config.kubeconfig:
        out.note(
            f"Kubeconfig: {kube_config.kubeconfig}",
            highlight=[str(kube_config.kubeconfig)],
        )
    if kube_config.context:
        out.note(f"Context: {kube_config.context}", highlight=[kube_config.context])
    if kube_config.namespace:
        out.note(
            f"Namespace: {kube_config.namespace}", highlight=[kube_config.namespace]
        )
