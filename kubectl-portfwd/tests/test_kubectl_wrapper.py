import asyncio
from unittest.mock import AsyncMock, patch

from portfwd.infrastructure.kubectl import start_port_forward


def _run_start(**kwargs) -> tuple:
    """Run start_port_forward with mocked subprocess and sleep; return the command args."""

    async def _inner():
        with (
            patch(
                "portfwd.infrastructure.kubectl.asyncio.create_subprocess_exec",
                new_callable=AsyncMock,
            ) as mock_exec,
            patch(
                "portfwd.infrastructure.kubectl.asyncio.sleep", new_callable=AsyncMock
            ),
        ):
            mock_proc = AsyncMock()
            mock_proc.pid = 1
            mock_exec.return_value = mock_proc
            await start_port_forward(**kwargs)
            return mock_exec.call_args.args

    return asyncio.run(_inner())


def test_start_port_forward_builds_correct_command():
    """`kubectl port-forward svc/<name> <local>:<remote> --namespace <ns>` is produced."""
    cmd = _run_start(
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
    cmd = _run_start(
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
    cmd = _run_start(
        namespace="ns",
        service="svc",
        local_port=5000,
        remote_port=80,
        context=None,
    )
    assert "--kubeconfig" not in cmd
    assert "--context" not in cmd
