from unittest.mock import AsyncMock, Mock, patch

import pytest
from kubek.kube.config import ResolvedKubeConfig
from portfwd.domain.models import (
    PortForwardPlan,
    ResolvedTargetRef,
    TargetKind,
)
from portfwd.infrastructure.kubectl_port_forward_launcher import (
    KubectlPortForwardLauncher,
    PortForwardProcess,
)


async def _launch(
    namespace: str,
    service: str,
    local_port: int,
    remote_port: int,
    context: str | None = None,
    kubeconfig: str | None = None,
    skip_tls_verify: bool = False,
    kind: TargetKind = TargetKind.SERVICE,
) -> tuple:
    plan = PortForwardPlan(
        target=ResolvedTargetRef(kind=kind, namespace=namespace, name=service),
        remote_port=remote_port,
        local_port=local_port,
    )
    config = ResolvedKubeConfig(
        context=context or "",
        namespace=namespace,
        kubeconfig=kubeconfig,
        skip_tls_verify=skip_tls_verify,
    )

    with patch(
        "portfwd.infrastructure.kubectl_port_forward_launcher.asyncio.create_subprocess_exec",
        new_callable=AsyncMock,
    ) as mock_exec:
        mock_proc = Mock()
        mock_proc.pid = 1
        mock_exec.return_value = mock_proc

        launcher = KubectlPortForwardLauncher(config=config)
        await launcher.launch(plan)

        return mock_exec.call_args.args


@pytest.mark.asyncio
async def test_start_port_forward_builds_correct_command():
    cmd = await _launch(
        namespace="my-ns",
        service="my-svc",
        local_port=5000,
        remote_port=80,
    )

    assert cmd[0] == "kubectl"
    assert "port-forward" in cmd
    assert "svc/my-svc" in cmd
    assert "5000:80" in cmd
    assert "--namespace" in cmd
    assert "my-ns" in cmd


@pytest.mark.asyncio
async def test_start_port_forward_builds_pod_command():
    cmd = await _launch(
        namespace="my-ns",
        service="my-pod",
        local_port=5000,
        remote_port=80,
        kind=TargetKind.POD,
    )

    assert "pod/my-pod" in cmd
    assert "svc/my-pod" not in cmd


@pytest.mark.asyncio
async def test_start_port_forward_includes_kubeconfig_and_context_when_given():
    cmd = await _launch(
        namespace="ns",
        service="svc",
        local_port=5000,
        remote_port=80,
        context="my-ctx",
        kubeconfig="/tmp/kcfg",
    )

    assert "--kubeconfig" in cmd
    assert "/tmp/kcfg" in cmd
    assert "--context" in cmd
    assert "my-ctx" in cmd


@pytest.mark.asyncio
async def test_port_forward_process_snapshot_reflects_subprocess_state():
    mock_proc = Mock()
    mock_proc.pid = 42
    mock_proc.returncode = 0

    session = PortForwardProcess(
        process=mock_proc,
        kind=TargetKind.SERVICE,
        local_port=5000,
        remote_port=80,
        name="svc",
        namespace="ns",
    )

    snapshot = session.snapshot()
    assert snapshot.pid == 42
    assert snapshot.returncode == 0
    assert snapshot.local_port == 5000
    assert snapshot.name == "svc"


@pytest.mark.asyncio
async def test_port_forward_process_terminate_ignores_missing_process():
    mock_proc = Mock()
    mock_proc.pid = 42
    mock_proc.returncode = None
    mock_proc.wait = AsyncMock()
    mock_proc.terminate = Mock(side_effect=ProcessLookupError)

    session = PortForwardProcess(
        process=mock_proc,
        kind=TargetKind.SERVICE,
        local_port=5000,
        remote_port=80,
        name="svc",
        namespace="ns",
    )

    session.terminate()


@pytest.mark.asyncio
async def test_start_port_forward_omits_optional_flags_when_not_given():
    cmd = await _launch(
        namespace="ns",
        service="svc",
        local_port=5000,
        remote_port=80,
    )

    assert "--kubeconfig" not in cmd
    assert "--context" not in cmd


@pytest.mark.asyncio
async def test_start_port_forward_includes_insecure_skip_tls_verify_when_given():
    cmd = await _launch(
        namespace="ns",
        service="svc",
        local_port=5000,
        remote_port=80,
        skip_tls_verify=True,
    )

    assert "--insecure-skip-tls-verify" in cmd


@pytest.mark.asyncio
async def test_start_port_forward_omits_insecure_skip_tls_verify_by_default():
    cmd = await _launch(
        namespace="ns",
        service="svc",
        local_port=5000,
        remote_port=80,
    )

    assert "--insecure-skip-tls-verify" not in cmd
