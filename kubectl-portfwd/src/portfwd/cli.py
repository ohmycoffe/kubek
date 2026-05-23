from __future__ import annotations

import asyncio
import itertools
import logging
from collections.abc import Iterable
from pathlib import Path
from subprocess import CalledProcessError
from typing import Annotated

import typer
from kubek.kube import (
    KubeConfig,
    KubeFacade,
    Service,
)
from kubek.term import create_output, setup_logging
from kubek.term.output import CLIOutput
from pydantic import ValidationError

from portfwd.config import (
    DEFAULT_CONFIG_PATH,
    GroupSpec,
    PortFwdConfig,
    load_config,
)
from portfwd.errors import (
    KubernetesError,
)
from portfwd.models import (
    NamespacedServiceName,
    NamespacedServiceNameSpec,
    ServicePortForwardPlan,
    ServicePortForwardSpec,
)
from portfwd.parser import parse_spec
from portfwd.plan import build_port_forward_plan
from portfwd.runner import manage_port_forwards
from portfwd.term import (
    SpecialGroups,
    ask_for_group,
    ask_for_namespace,
    ask_for_service,
)

logger = logging.getLogger(__name__)

app = typer.Typer()


def _convert_to_spec(services: Iterable[Service]) -> list[ServicePortForwardSpec]:
    specs = [
        ServicePortForwardSpec(
            target=NamespacedServiceNameSpec(
                namespace=svc.metadata.namespace,
                name=svc.metadata.name,
            ),
            remote_port=port.port,
        )
        for svc in sorted(
            services, key=lambda s: (s.metadata.namespace, s.metadata.name)
        )
        for port in sorted(svc.spec.ports, key=lambda x: x.port)
    ]
    return specs


def _fetch_services_for_namespaces(
    namespaces: list[str], api: KubeFacade
) -> list[ServicePortForwardSpec]:
    raw = itertools.chain.from_iterable(
        api.service.list(namespace=namespace) for namespace in namespaces
    )
    return _convert_to_spec(raw)


def _extract_group(group_name: str, available: list[GroupSpec]) -> GroupSpec | None:
    for group in available:
        if group.name == group_name:
            return group
    return None


def _validate_group(group: str, available: list[GroupSpec]) -> None:
    available_groups = {g.name for g in available}
    if not available:
        raise typer.BadParameter("No groups defined in config file.")
    if group not in available_groups:
        raise typer.BadParameter(
            f'error: unknown group "{group}" for "--group" flag '
            f"(available: {', '.join(sorted(available_groups))})"
        )


def _run_group(group_name: str, cfg: PortFwdConfig, api: KubeFacade) -> None:
    _validate_group(group_name, cfg.groups)
    group_obj = _extract_group(group_name, cfg.groups)
    assert group_obj is not None
    plans: list[ServicePortForwardPlan] = [
        ServicePortForwardPlan(
            target=NamespacedServiceName(name=svc.name, namespace=svc.namespace),
            remote_port=svc.remote_port,
            local_port=svc.local_port,
        )
        for svc in group_obj.services
    ]
    asyncio.run(manage_port_forwards(plans, api=api))


def _run_services(service: list[str], cfg: PortFwdConfig, api: KubeFacade) -> None:
    plans: list[ServicePortForwardPlan] = []
    for svc in service:
        spec = parse_spec(svc)
        plans.append(build_port_forward_plan(spec=spec, config=cfg, api=api))
    asyncio.run(manage_port_forwards(plans, api=api))


def _run_interactive(cfg: PortFwdConfig, api: KubeFacade, out: CLIOutput) -> None:
    with out.progress("Fetching namespaces…"):
        namespaces = [ns.metadata.name for ns in api.namespace.list()]
    selected_namespaces = ask_for_namespace(namespaces, api.current_config.namespace)
    if not selected_namespaces:
        out.problem("No namespaces selected. Exiting.")
        raise typer.Exit(code=0)
    with out.progress("Fetching services…"):
        try:
            specs = _fetch_services_for_namespaces(selected_namespaces, api)
        except Exception:
            out.problem("Failed to fetch services.")
            raise typer.Exit(code=1) from None
    if not specs:
        out.problem("No services found.")
        raise typer.Exit(code=0)

    selected: list[ServicePortForwardSpec] = ask_for_service(specs)
    if not selected:
        out.problem("No services selected. Exiting.")
        raise typer.Exit(code=0)
    plans: list[ServicePortForwardPlan] = []
    for spec in selected:
        plans.append(build_port_forward_plan(spec=spec, config=cfg, api=api))
    asyncio.run(manage_port_forwards(plans=plans, api=api))


def _run_port_forwards(
    cfg: PortFwdConfig,
    group: str | None,
    service: list[str] | None,
    api: KubeFacade,
    out: CLIOutput,
) -> None:
    """Run port-forwards for --service, --group, or the interactive picker."""
    if service is not None:
        _run_services(service, cfg, api)
        return
    if group is not None:
        _run_group(group, cfg, api)
        return
    group_obj = ask_for_group(cfg.groups)
    if group_obj is SpecialGroups.CUSTOM:
        _run_interactive(cfg, api, out)
    else:
        _run_group(group_obj.name, cfg, api)


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
    out = create_output(verbosity_count=verbose)  #
    setup_logging(verbose, "kubek", "portfwd")

    if group is not None and service is not None:
        raise typer.BadParameter("'--group' and '--service' are mutually exclusive.")

    kubeconfig_path = str(kubeconfig) if kubeconfig is not None else None
    if kubeconfig_path:
        out.note(f"Kubeconfig: {kubeconfig_path}", [kubeconfig_path])

    try:
        api = KubeFacade.from_config(
            config=KubeConfig(
                context=context,
                kubeconfig=kubeconfig_path,
            )
        )
    except Exception:
        out.exception("Failed to initialize connection to Kubernetes cluster")
        raise typer.Exit(code=1) from None

    if api.current_config.context:
        out.note(f"Context: {api.current_config.context}", [api.current_config.context])
    if api.current_config.namespace:
        out.note(
            f"Namespace: {api.current_config.namespace}", [api.current_config.namespace]
        )

    try:
        cfg = load_config(config)
    except FileNotFoundError as e:
        out.exception(f"Config file not found: {e.filename}")
        raise typer.Exit(code=1) from None
    except ValidationError:
        out.exception("Invalid configuration.")
        raise typer.Exit(code=1) from None
    except ValueError:
        out.exception("Unexpected error loading configuration.")
        raise typer.Exit(code=1) from None

    try:
        _run_port_forwards(cfg, group, service, api, out)
    except KubernetesError:
        out.exception("Failed to set up port-forwards")
        raise typer.Exit(code=1) from None
    except ValidationError as e:
        out.exception("Invalid configuration.")
        raise typer.BadParameter(str(e)) from None
    except ValueError as e:
        out.exception("Unexpected error loading configuration.")
        raise typer.BadParameter(str(e)) from None
    except CalledProcessError:
        out.exception("kubectl call failed")
        raise typer.Exit(code=1) from None
