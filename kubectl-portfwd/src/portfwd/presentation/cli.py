from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated

import typer
from kubek.kube import KubeClientError, KubeConfig, KubeFacade, ResolvedKubeConfig
from kubek.net import is_port_free
from kubek.term import (
    CLIOutput,
    create_output,
    set_logger_levels_from_verbosity_count,
    suppress_logging,
)

from portfwd.application.port_forwarding.events import PortForwardEvent
from portfwd.application.port_forwarding.streamer import PortForwardEventStreamer
from portfwd.application.ports import KubeGateway
from portfwd.application.queries import fetch_targets_for_namespaces
from portfwd.application.use_case import (
    PortForwardUseCase,
)
from portfwd.domain.errors import (
    EmptySpecFileError,
    InvalidTargetSpecError,
    NoSelectionError,
    NoTargetsFoundError,
    PortForwardError,
    SpecFileLoadError,
)
from portfwd.domain.models import PortForwardSpec
from portfwd.infrastructure.kubectl_port_forward_launcher import (
    KubectlPortForwardLauncher,
)
from portfwd.infrastructure.spec_file_loader import load_spec_file
from portfwd.presentation.display import PortForwardLiveDisplay
from portfwd.presentation.prompts import (
    ask_for_kinds,
    ask_for_namespace,
    ask_for_targets,
)
from portfwd.presentation.spec_parser import (
    format_spec_file_line_error,
    parse_spec,
)

logger = logging.getLogger(__name__)

app = typer.Typer()


@app.callback(invoke_without_command=True)
def port_forward(
    file: Annotated[
        Path | None,
        typer.Option(
            "--file",
            "-f",
            exists=True,
            file_okay=True,
            dir_okay=False,
            resolve_path=True,
            help=(
                "Path to a spec file listing targets to forward, one per line "
                '(each "[namespace/]type/name[:remote_port][::local_port]").'
            ),
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
    target: Annotated[
        list[str] | None,
        typer.Option(
            "--target",
            "-t",
            help=(
                "Target to forward as "
                '"[namespace/]type/name[:remote_port][::local_port]", '
                "where type is pod or svc (e.g. kube-public/svc/auth:8080). "
                "Can be specified multiple times."
            ),
        ),
    ] = None,
    insecure_skip_tls_verify: Annotated[
        bool,
        typer.Option(
            "--insecure-skip-tls-verify",
            help="Disable TLS certificate verification for the Kubernetes API (kubek client only).",
        ),
    ] = False,
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
    """Interactive kubectl port-forward for Kubernetes services and pods.

    \b
    Examples:
        kubectl portfwd
        kubectl portfwd -f .portfwd-plan
        kubectl portfwd -t kube-public/svc/auth-service
        kubectl portfwd -t kube-public/svc/auth-service:8080
        kubectl portfwd -t kube-public/svc/auth-service:8080::50000
        kubectl portfwd -t kube-public/svc/auth -t kube-public/pod/worker-xyz:9000
    """
    set_logger_levels_from_verbosity_count(verbose, "kubek", "portfwd")
    out: CLIOutput = create_output(verbosity_count=verbose)

    if file is not None and target is not None:
        raise typer.BadParameter("'--file' and '--target' are mutually exclusive.")

    kubeconfig_str = str(kubeconfig) if kubeconfig else None

    try:
        kube_config = KubeConfig(
            context=context,
            kubeconfig=kubeconfig_str,
            skip_tls_verify=insecure_skip_tls_verify,
        )
        api = KubeFacade.from_config(config=kube_config)
        _print_kubeconfig(out, api.current_config)

        display = PortForwardLiveDisplay(
            context=api.current_config.context,
            console=out.console,
        )

        use_case = PortForwardUseCase(
            api=api,
            streamer=PortForwardEventStreamer(
                launcher=KubectlPortForwardLauncher(config=api.current_config),
                is_local_port_free=is_port_free,
            ),
        )
        run_port_forwards_from_cli(
            file=file,
            target=target,
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


def _print_kubeconfig(out: CLIOutput, kube_config: ResolvedKubeConfig) -> None:
    if kube_config.kubeconfig:
        out.note(
            f"Kubeconfig: {kube_config.kubeconfig}",
            highlight=[str(kube_config.kubeconfig)],
        )
    if kube_config.context:
        out.note(f"Context: {kube_config.context}", highlight=[kube_config.context])


async def _run_event_stream(
    display: PortForwardLiveDisplay,
    event_stream: AsyncIterator[PortForwardEvent],
) -> None:
    with suppress_logging(), display.live():
        async for event in event_stream:
            display.apply(event)


def run_port_forwards_from_cli(
    *,
    file: Path | None,
    target: list[str] | None,
    api: KubeGateway,
    out: CLIOutput,
    use_case: PortForwardUseCase,
    display: PortForwardLiveDisplay,
) -> None:
    """Dispatch to the correct port-forward flow based on CLI flags.

    - ``--target`` wins outright.
    - ``--file`` loads targets from a spec file.
    - Otherwise prompt the user to pick targets interactively.
    """
    if target is not None and file is not None:
        raise ValueError("'file' and 'target' cannot both be provided")

    if target is not None:
        specs = [parse_spec(value) for value in target]
        asyncio.run(_run_event_stream(display, use_case.stream_specs(specs)))
        return
    if file is not None:
        specs = _load_spec_file(file)
        asyncio.run(_run_event_stream(display, use_case.stream_specs(specs)))
        return

    specs = _ask_for_targets(api=api, out=out)
    asyncio.run(_run_event_stream(display, use_case.stream_specs(specs)))


def _load_spec_file(path: Path) -> list[PortForwardSpec]:
    try:
        lines = load_spec_file(path)
    except FileNotFoundError as e:
        raise SpecFileLoadError(f"spec file not found: {e.filename}") from e

    if not lines:
        raise EmptySpecFileError(f"spec file contains no targets: {path}")

    display_path = _display_path(path)
    specs: list[PortForwardSpec] = []
    for entry in lines:
        try:
            specs.append(parse_spec(entry.value))
        except InvalidTargetSpecError as e:
            raise SpecFileLoadError(
                format_spec_file_line_error(
                    path=display_path,
                    line=entry.line,
                    text=entry.value,
                )
            ) from e
    return specs


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _ask_for_targets(api: KubeGateway, out: CLIOutput) -> list[PortForwardSpec]:
    selected_kinds = ask_for_kinds()

    if not selected_kinds:
        raise NoSelectionError("no resource types selected")

    with out.progress("Fetching namespaces…"):
        namespaces = [ns.metadata.name for ns in api.namespace.list()]

    selected_namespaces = ask_for_namespace(
        all_namespaces=namespaces,
        current_namespace=api.current_config.namespace,
    )

    if not selected_namespaces:
        raise NoSelectionError("no namespaces selected")

    with out.progress("Fetching resources…"):
        specs = fetch_targets_for_namespaces(
            api=api,
            namespaces=selected_namespaces,
            kinds=selected_kinds,
        )

    if not specs:
        raise NoTargetsFoundError(
            "no matching resources found in the selected namespaces"
        )

    selected_targets = ask_for_targets(specs)

    if not selected_targets:
        raise NoSelectionError("no targets selected")

    return selected_targets
