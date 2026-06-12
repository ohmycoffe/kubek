import asyncio
from unittest.mock import AsyncMock, patch

from kubek.kube.config import ResolvedKubeConfig
from portfwd.domain.models import NamespacedServiceNamePlan, ServicePortForwardPlan
from portfwd.infrastructure.kubectl_port_forward_launcher import (
    KubectlPortForwardLauncher,
)


def _run_launch(**kwargs) -> tuple:
    """Run launcher.launch with mocked subprocess; return the command args."""
    namespace = kwargs.pop("namespace")
    service = kwargs.pop("service")
    local_port = kwargs.pop("local_port")
    remote_port = kwargs.pop("remote_port")
    context = kwargs.pop("context", None)
    kubeconfig = kwargs.pop("kubeconfig", None)

    plan = ServicePortForwardPlan(
        target=NamespacedServiceNamePlan(namespace=namespace, name=service),
        remote_port=remote_port,
        local_port=local_port,
    )
    config = ResolvedKubeConfig(
        context=context or "",
        namespace=namespace,
        kubeconfig=kubeconfig,
    )

    async def _inner():
        with patch(
            "portfwd.infrastructure.kubectl_port_forward_launcher.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.pid = 1
            mock_exec.return_value = mock_proc
            launcher = KubectlPortForwardLauncher(config=config)
            await launcher.launch(plan)
            return mock_exec.call_args.args

    return asyncio.run(_inner())


def test_start_port_forward_builds_correct_command():
    """`kubectl port-forward svc/<name> <local>:<remote> --namespace <ns>` is produced."""
    cmd = _run_launch(
        namespace="my-ns",
        service="my-svc",
        local_port=5000,
        remote_port=80,
        context=None,
    )
    assert cmd[0] == "kubectl"
    assert "port-forward" in cmd
    assert "svc/my-svc" in cmd
    assert "5000:80" in cmd
    assert "--namespace" in cmd
    assert "my-ns" in cmd


def test_start_port_forward_includes_kubeconfig_and_context_when_given():
    """--kubeconfig and --context flags are present when the caller supplies them."""
    cmd = _run_launch(
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


def test_start_port_forward_omits_optional_flags_when_not_given():
    """--kubeconfig and --context are absent when not provided."""
    cmd = _run_launch(
        namespace="ns",
        service="svc",
        local_port=5000,
        remote_port=80,
        context=None,
    )
    assert "--kubeconfig" not in cmd
    assert "--context" not in cmd
