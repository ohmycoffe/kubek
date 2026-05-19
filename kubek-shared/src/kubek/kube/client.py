from __future__ import annotations

import logging
import shlex
import subprocess
from collections.abc import Sequence

from kubek.kube.schemas import (
    Config,
    ConfigMap,
    Deployment,
    DeploymentList,
    Namespace,
    NamespaceList,
    Secret,
    Service,
    ServiceList,
    WorkflowTemplate,
    WorkflowTemplateList,
)

logger = logging.getLogger(__name__)

DEFAULT_NAMESPACE = "default"


class KubectlError(Exception):
    """Base error for kubectl operations"""

    def __init__(
        self,
        cmd: Sequence[str],
        returncode: int,
        stdout: str | None,
        stderr: str | None,
        msg: str | None = None,
    ):
        self.cmd = list(cmd)
        if returncode == 0:
            raise ValueError("returncode must be non-zero for an error")

        self.returncode: int = returncode
        self.stdout: str = stdout or ""
        self.stderr: str = stderr or ""
        self.msg: str | None = msg

        super().__init__(self.__str__())

    def __str__(self) -> str:
        if self.msg:
            return str(self.msg)
        else:
            return f"{shlex.join(self.cmd)} failed with code {self.returncode}"


class ContextNotSetError(KubectlError):
    """Error raised when kubectl context is not set"""


class NotFoundError(KubectlError):
    """Error raised when a specified resource is not found"""


class AmbiguousResourceError(Exception):
    """Error raised when a resource lookup returns multiple results"""


def _run(cmd: list[str]) -> str:
    """Execute a subprocess command and return stdout.

    Args:
        cmd: Command as list of strings.

    Returns:
        Command stdout as string.

    Raises:
        CalledProcessError: If command returns non-zero exit code.
    """
    logger.debug("%s", shlex.join(cmd))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        logger.debug("Command failed (exit %d)", e.returncode)
        if e.stderr:
            logger.debug("stderr:\n%s", e.stderr.strip())
        if e.stdout:
            logger.debug("stdout:\n%s", e.stdout.strip())
        err = _error_factory(
            cmd=e.cmd,
            returncode=e.returncode,
            stdout=e.stdout,
            stderr=e.stderr,
        )
        raise err from None
    return result.stdout


def _error_factory(
    cmd: Sequence[str], returncode: int, stdout: str | None, stderr: str | None
) -> KubectlError:
    """Factory to create appropriate KubectlError subclass based on stderr content."""
    stderr_str = stderr or ""
    if "error: current-context is not set" in stderr_str:
        return ContextNotSetError(cmd, returncode, stdout, stderr_str)
    elif "NotFound" in stderr_str:
        return NotFoundError(cmd, returncode, stdout, stderr_str)
    return KubectlError(cmd, returncode, stdout, stderr_str)


class KubectlWrapper:
    """Wrapper around kubectl commands."""

    def __init__(
        self,
        context: str | None = None,
        namespace: str | None = None,
        kubeconfig: str | None = None,
    ) -> None:
        self.context = context
        self.namespace = namespace
        self.kubeconfig = kubeconfig

    @staticmethod
    def global_kubectl_args(
        kubeconfig: str | None = None,
        context: str | None = None,
        namespace: str | None = None,
    ) -> list[str]:
        """Build shared kubectl global flags (kubeconfig, context, namespace)."""
        args: list[str] = []
        if kubeconfig:
            args.extend(["--kubeconfig", kubeconfig])
        if context:
            args.extend(["--context", context])
        if namespace:
            args.extend(["--namespace", namespace])
        return args

    def __args(self, namespace: str | None = None) -> list[str]:
        """Return kubectl global flags for this wrapper instance."""
        ns = namespace or self.namespace
        ctx = self.context
        kubeconfig = self.kubeconfig
        return self.global_kubectl_args(
            kubeconfig=kubeconfig, context=ctx, namespace=ns
        )

    @staticmethod
    def get_config(
        kubeconfig: str | None = None,
        context: str | None = None,
        minify: bool = False,
    ) -> Config:
        """Get the full kubeconfig as a Config object."""
        args = KubectlWrapper.global_kubectl_args(
            kubeconfig=kubeconfig, context=context
        )
        minify_args = ["--minify"] if minify else []
        raw = _run(["kubectl", *args, "config", "view", *minify_args, "-o", "json"])
        return Config.model_validate_json(raw)

    def get_namespaces(self) -> list[Namespace]:
        """Get the list of available Kubernetes namespaces."""
        args = self.__args()
        raw = _run(["kubectl", *args, "get", "namespaces", "-o", "json"])
        parsed = NamespaceList.model_validate_json(raw)
        return [el for el in parsed.items]

    def get_services(self, namespace: str | None = None) -> list[Service]:
        """Get services with their ports in the specified namespace."""

        args = self.__args(namespace=namespace)
        raw = _run(["kubectl", *args, "get", "services", "-o", "json"])
        services = ServiceList.model_validate_json(raw)
        return services.items

    def get_service(
        self,
        name: str,
        namespace: str | None = None,
    ) -> Service | None:
        """Look up a single service by name. Returns None if not found, raises AmbiguousResourceError if multiple match."""
        args = self.__args(namespace=namespace)
        raw = _run(
            [
                "kubectl",
                *args,
                "get",
                "svc",
                "--field-selector",
                f"metadata.name={name}",
                "-o",
                "json",
            ]
        )
        services = ServiceList.model_validate_json(raw)
        if len(services.items) > 1:
            raise AmbiguousResourceError(
                f'multiple services named "{name}" found in namespace "{namespace}"'
            )
        return services.items[0] if services.items else None

    def get_secret(self, name: str, namespace: str | None = None) -> Secret:
        args = self.__args(namespace=namespace)
        cmd = [
            "kubectl",
            *args,
            "get",
            "secret",
            name,
            "-o",
            "json",
        ]
        raw = _run(cmd)
        secret = Secret.model_validate_json(raw)
        return secret

    def get_configmap(self, name: str, namespace: str | None = None) -> ConfigMap:
        args = self.__args(namespace=namespace)
        cmd: list[str] = [
            "kubectl",
            *args,
            "get",
            "configmap",
            name,
            "-o",
            "json",
        ]
        raw = _run(cmd)
        configmap = ConfigMap.model_validate_json(raw)
        return configmap

    def get_deployments(self, namespace: str | None = None) -> list[Deployment]:
        """List deployment names in the specified namespace."""
        args = self.__args(namespace=namespace)
        raw = _run(["kubectl", *args, "get", "deployment", "-o", "json"])
        parsed = DeploymentList.model_validate_json(raw)
        return [el for el in parsed.items]

    def get_deployment(self, name: str, namespace: str | None = None) -> Deployment:
        """Get deployment by name in the specified namespace."""
        args = self.__args(namespace=namespace)

        cmd = ["kubectl", *args, "get", "deployment", name, "-o", "json"]
        raw = _run(cmd)
        return Deployment.model_validate_json(raw)

    def get_workflowtemplates(
        self, namespace: str | None = None
    ) -> list[WorkflowTemplate]:
        """List WorkflowTemplate names in the specified namespace."""

        args = self.__args(namespace=namespace)
        raw = _run(["kubectl", *args, "get", "workflowtemplate", "-o", "json"])
        parsed = WorkflowTemplateList.model_validate_json(raw)
        return [el for el in parsed.items]

    def get_workflowtemplate(
        self, name: str, namespace: str | None = None
    ) -> WorkflowTemplate:
        """Get a single WorkflowTemplate by name in the specified namespace."""

        args = self.__args(namespace=namespace)
        cmd = ["kubectl", *args, "get", "workflowtemplate", name, "-o", "json"]
        raw = _run(cmd)
        return WorkflowTemplate.model_validate_json(raw)
