from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated

import typer
from kubek.kube import KubeClientError, KubeConfig, KubeFacade, ResolvedKubeConfig
from kubek.term import CLIOutput, create_output, setup_logging_from_count
from pydantic import ValidationError

from portfwd.application.port_forwarding.events import PortForwardEvent
from portfwd.application.port_forwarding.streamer import PortForwardEventStreamer
from portfwd.application.ports import KubeGateway
from portfwd.application.queries import fetch_services_for_namespaces
from portfwd.application.use_case import (
    PortForwardUseCase,
)
from portfwd.domain.config import PortFwdConfig, SpecialGroups
from portfwd.domain.errors import (
    ConfigLoadError,
    NoSelectionError,
    NoServicesFoundError,
    PortForwardError,
)
from portfwd.domain.models import ServicePortForwardSpec
from portfwd.infrastructure.config_loader import DEFAULT_CONFIG_PATH, load_config
from portfwd.infrastructure.kubectl_port_forward_launcher import (
    KubectlPortForwardLauncher,
)
from portfwd.presentation.display import PortForwardLiveDisplay
from portfwd.presentation.prompts import (
    ask_for_group,
    ask_for_namespace,
    ask_for_service,
)
from portfwd.presentation.service_parser import parse_spec

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

        portfwd_config = _load_config(config)

        display = PortForwardLiveDisplay(context=api.current_config.context)

        use_case = PortForwardUseCase(
            api=api,
            config=portfwd_config,
            streamer=PortForwardEventStreamer(
                launcher=KubectlPortForwardLauncher(config=api.current_config)
            ),
        )
        run_port_forwards_from_cli(
            cfg=portfwd_config,
            group=group,
            service=service,
            api=api,
            out=out,
            use_case=use_case,
            display=display,
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


async def _run_event_stream(
    display: PortForwardLiveDisplay,
    event_stream: AsyncIterator[PortForwardEvent],
) -> None:
    with display.live():
        async for event in event_stream:
            display.apply(event)


def run_port_forwards_from_cli(
    *,
    cfg: PortFwdConfig,
    group: str | None,
    service: list[str] | None,
    api: KubeGateway,
    out: CLIOutput,
    use_case: PortForwardUseCase,
    display: PortForwardLiveDisplay,
) -> None:
    """Dispatch to the correct port-forward flow based on CLI flags.

    - `--service` wins outright.
    - `--group` runs that group.
    - Otherwise prompt the user to pick a group (or 'custom' interactive flow).
    """
    if service is not None:
        specs = [parse_spec(value) for value in service]
        asyncio.run(_run_event_stream(display, use_case.stream_specs(specs)))
        return
    if group is not None:
        asyncio.run(_run_event_stream(display, use_case.stream_group(group_name=group)))
        return

    selection = ask_for_group(cfg.groups)
    if selection is SpecialGroups.CUSTOM:
        specs = _ask_for_custom_services(api=api, out=out)
        asyncio.run(_run_event_stream(display, use_case.stream_specs(specs)))
    else:
        asyncio.run(
            _run_event_stream(display, use_case.stream_group(group_name=selection.name))
        )


def _ask_for_custom_services(
    api: KubeGateway,
    out: CLIOutput,
) -> list[ServicePortForwardSpec]:
    with out.progress("Fetching namespaces…"):
        namespaces = [ns.metadata.name for ns in api.namespace.list()]

    selected_namespaces = ask_for_namespace(
        all_namespaces=namespaces,
        current_namespace=api.current_config.namespace,
    )

    if not selected_namespaces:
        raise NoSelectionError("no namespaces selected")

    with out.progress("Fetching services…"):
        specs = fetch_services_for_namespaces(
            api=api,
            namespaces=selected_namespaces,
        )

    if not specs:
        raise NoServicesFoundError("no services found in the selected namespaces")

    selected_services = ask_for_service(specs)

    if not selected_services:
        raise NoSelectionError("no services selected")

    return selected_services
