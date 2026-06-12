import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from kubek.kube.dto.service import Service
from portfwd.application.port_forwarding.events import (
    PortForwardEvent,
    PortForwardEventType,
)
from portfwd.application.port_forwarding.planner import (
    build_port_forward_plan,
    resolve_local_port,
    resolve_remote_port,
)
from portfwd.application.port_forwarding.snapshot import PortForwardProcessSnapshot
from portfwd.domain.config import PortFwdConfig, ServicePortForwardDefaults
from portfwd.domain.errors import (
    AmbiguousServicePortError,
    MissingNamespaceError,
    NoServicePortsError,
    ServiceNotFoundError,
)
from portfwd.domain.models import NamespacedServiceNameSpec, ServicePortForwardSpec
from portfwd.infrastructure.kubectl_port_forward_launcher import PortForwardProcess


def _make_process(
    service_name: str, remote_port: int, local_port: int, returncode: int = 0
) -> PortForwardProcess:
    """Build a PortForwardProcess wrapping a mocked asyncio subprocess."""
    proc = MagicMock()
    proc.pid = 1234
    proc.returncode = returncode
    proc.wait = AsyncMock()
    return PortForwardProcess(
        process=proc,
        service_name=service_name,
        remote_port=remote_port,
        local_port=local_port,
        namespace="ns",
    )


_SVC_CONFIG = ServicePortForwardDefaults(
    name="svc", namespace="ns", remote_port=80, local_port=9000
)


def test_resolve_local_port_uses_configured_port():
    """Returns the configured local_port when a matching config entry exists."""
    config = PortFwdConfig(defaults=[_SVC_CONFIG])
    assert resolve_local_port("svc", "ns", 80, config) == 9000


def test_resolve_local_port_uses_deterministic_port_when_free():
    """Returns the deterministic port when no config match and the port is free."""
    config = PortFwdConfig()
    with (
        patch(
            "portfwd.application.port_forwarding.planner.get_deterministic_port",
            return_value=55000,
        ),
        patch(
            "portfwd.application.port_forwarding.planner.is_port_free",
            return_value=True,
        ),
    ):
        assert resolve_local_port("svc", "ns", 80, config) == 55000


def test_resolve_local_port_falls_back_to_free_port_when_deterministic_taken():
    """Falls back to find_free_port when the deterministic port is already in use."""
    config = PortFwdConfig()
    with (
        patch(
            "portfwd.application.port_forwarding.planner.get_deterministic_port",
            return_value=55000,
        ),
        patch(
            "portfwd.application.port_forwarding.planner.is_port_free",
            return_value=False,
        ),
        patch(
            "portfwd.application.port_forwarding.planner.find_free_port",
            return_value=50000,
        ),
    ):
        assert resolve_local_port("svc", "ns", 80, config) == 50000


def test_resolve_local_port_ignores_config_from_other_namespace():
    """Does not use a config entry whose namespace does not match."""
    other_ns = ServicePortForwardDefaults(
        name="svc", namespace="other-ns", remote_port=80, local_port=9000
    )
    config = PortFwdConfig(defaults=[other_ns])
    with (
        patch(
            "portfwd.application.port_forwarding.planner.get_deterministic_port",
            return_value=55000,
        ),
        patch(
            "portfwd.application.port_forwarding.planner.is_port_free",
            return_value=False,
        ),
        patch(
            "portfwd.application.port_forwarding.planner.find_free_port",
            return_value=50000,
        ),
    ):
        assert resolve_local_port("svc", "ns", 80, config) == 50000


def _make_snapshot(
    service_name: str,
    remote_port: int = 80,
    local_port: int = 9000,
    pid: int = 1234,
    returncode: int | None = None,
) -> PortForwardProcessSnapshot:
    return PortForwardProcessSnapshot(
        namespace="ns",
        service_name=service_name,
        remote_port=remote_port,
        local_port=local_port,
        pid=pid,
        returncode=returncode,
    )


async def _collect_events_from_queue(
    processes: list[PortForwardProcess],
    expected_shutdown: asyncio.Event,
) -> list[PortForwardEvent]:
    """Mirror stream_port_forwards queue draining for pre-started processes."""
    event_queue: asyncio.Queue[PortForwardEvent] = asyncio.Queue()
    running = 0

    for proc in processes:
        event_queue.put_nowait(
            PortForwardEvent(
                type=PortForwardEventType.STARTED,
                snapshot=proc.snapshot(),
            )
        )
        running += 1

    async def watch(process: PortForwardProcess) -> None:
        await process.process.wait()
        if expected_shutdown.is_set():
            event_type = PortForwardEventType.STOPPED
        else:
            event_type = PortForwardEventType.DIED
        event_queue.put_nowait(
            PortForwardEvent(type=event_type, snapshot=process.snapshot())
        )

    async with asyncio.TaskGroup() as tg:
        for proc in processes:
            tg.create_task(watch(proc))

        events: list[PortForwardEvent] = []
        while running > 0:
            event = await event_queue.get()
            if event.exited:
                running -= 1
            events.append(event)
        return events


def test_stream_yields_died_when_process_exits_unexpectedly():
    """DIED is yielded when the process exits and shutdown was not expected."""
    proc = _make_process("svc", remote_port=80, local_port=9000, returncode=1)

    events = asyncio.run(_collect_events_from_queue([proc], asyncio.Event()))

    assert events[0].type == PortForwardEventType.STARTED
    assert events[-1].type == PortForwardEventType.DIED
    assert events[-1].snapshot.service_name == "svc"
    assert events[-1].snapshot.returncode == 1


def test_stream_yields_stopped_when_shutdown_expected():
    """STOPPED is yielded when the process exits and shutdown was expected."""
    proc = _make_process("svc", remote_port=80, local_port=9000, returncode=0)

    shutdown = asyncio.Event()
    shutdown.set()
    events = asyncio.run(_collect_events_from_queue([proc], shutdown))

    assert events[0].type == PortForwardEventType.STARTED
    assert events[-1].type == PortForwardEventType.STOPPED
    assert events[-1].snapshot.service_name == "svc"


def _make_service(name: str, namespace: str, ports: list[int]) -> Service:
    return Service.model_validate(
        {
            "metadata": {"name": name, "namespace": namespace},
            "spec": {"ports": [{"port": p, "protocol": "TCP"} for p in ports]},
        }
    )


def test_resolve_remote_port_returns_single_port():
    """Returns the port number when the service has exactly one port."""
    service = _make_service("svc", "ns", [8080])
    assert resolve_remote_port(service) == 8080


def test_resolve_remote_port_raises_when_no_ports():
    """NoServicePortsError is raised for services with no declared ports."""
    service = _make_service("svc", "ns", [])
    with pytest.raises(NoServicePortsError):
        resolve_remote_port(service)


def test_resolve_remote_port_raises_when_multiple_ports():
    """AmbiguousServicePortError is raised when the service exposes more than one port."""
    service = _make_service("svc", "ns", [80, 8080])
    with pytest.raises(AmbiguousServicePortError):
        resolve_remote_port(service)


def _make_api(namespace=None, services=None):
    """Minimal fake KubeFacade: only the attributes used by build_port_forward_plan."""
    services_map = {(ns, name): svc for (ns, name), svc in (services or {}).items()}

    class FakeServiceRepo:
        def get(self, name, namespace=None):
            return services_map.get((namespace, name))

    return SimpleNamespace(
        current_config=SimpleNamespace(namespace=namespace, context=None),
        service=FakeServiceRepo(),
    )


def test_build_port_forward_plan_uses_spec_ports_directly():
    """Ports declared in the spec are forwarded unchanged; no Service lookup needed."""
    svc = _make_service("auth", "ns", [80])
    api = _make_api(namespace="ns", services={("ns", "auth"): svc})
    spec = ServicePortForwardSpec(
        target=NamespacedServiceNameSpec(name="auth", namespace="ns"),
        remote_port=443,
        local_port=9443,
    )
    plan = build_port_forward_plan(spec, PortFwdConfig(), api)
    assert plan.remote_port == 443
    assert plan.local_port == 9443
    assert plan.target.namespace == "ns"
    assert plan.target.name == "auth"


def test_build_port_forward_plan_uses_api_namespace_when_absent_in_spec():
    """api.current_config.namespace is used when the spec has no namespace."""
    svc = _make_service("auth", "kube-public", [80])
    api = _make_api(namespace="kube-public", services={("kube-public", "auth"): svc})
    spec = ServicePortForwardSpec(
        target=NamespacedServiceNameSpec(name="auth"),
        remote_port=80,
        local_port=9000,
    )
    plan = build_port_forward_plan(spec, PortFwdConfig(), api)
    assert plan.target.namespace == "kube-public"


def test_build_port_forward_plan_raises_when_namespace_missing():
    """MissingNamespaceError is raised when neither spec nor api supplies a namespace."""
    svc = _make_service("auth", "ns", [80])
    api = _make_api(namespace=None, services={("ns", "auth"): svc})
    spec = ServicePortForwardSpec(
        target=NamespacedServiceNameSpec(name="auth"),
        remote_port=80,
        local_port=9000,
    )
    with pytest.raises(MissingNamespaceError):
        build_port_forward_plan(spec, PortFwdConfig(), api)


def test_build_port_forward_plan_raises_when_service_not_found():
    """ServiceNotFoundError is raised when the Service does not exist in the namespace."""
    api = _make_api(namespace="ns")
    spec = ServicePortForwardSpec(
        target=NamespacedServiceNameSpec(name="missing", namespace="ns"),
        remote_port=80,
        local_port=9000,
    )
    with pytest.raises(ServiceNotFoundError):
        build_port_forward_plan(spec, PortFwdConfig(), api)


def test_build_port_forward_plan_resolves_remote_port_from_service():
    """When spec has no remote_port, it is read from the service's single declared port."""
    svc = _make_service("auth", "ns", [8080])
    api = _make_api(namespace="ns", services={("ns", "auth"): svc})
    spec = ServicePortForwardSpec(
        target=NamespacedServiceNameSpec(name="auth", namespace="ns"),
        local_port=9000,
    )
    plan = build_port_forward_plan(spec, PortFwdConfig(), api)
    assert plan.remote_port == 8080
