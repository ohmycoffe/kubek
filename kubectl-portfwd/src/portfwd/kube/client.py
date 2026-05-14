from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from kubek.kube import call_subprocess

logger = logging.getLogger(__name__)

DEFAULT_NAMESPACE = "default"


@dataclass
class KubernetesService:
    name: str
    port: int
    protocol: str
    namespace: str


def parse_context(raw: str) -> str:
    """Extract cluster name from a kubectl context string,
    stripping EKS ARN prefix if present.
    """
    assert raw is not None, "Context string is empty"
    context = raw.strip()
    if context.startswith("arn:aws:eks:"):
        return context.split("/")[-1]
    return context


def parse_namespaces(raw: str) -> list[str]:
    """Parse namespace names from `kubectl get namespaces -o json` output."""
    data = json.loads(raw)
    return [el["metadata"]["name"] for el in data["items"]]


def parse_services(raw: str, namespace: str) -> list[KubernetesService]:
    """Parse services from `kubectl get services -o json` output,
    skipping the built-in kubernetes service.
    """
    data = json.loads(raw)
    services: list[KubernetesService] = []
    for svc in data["items"]:
        name = svc["metadata"]["name"]
        if name == "kubernetes":
            continue
        for port in svc["spec"]["ports"]:
            services.append(
                KubernetesService(
                    name=name,
                    port=port["port"],
                    protocol=port["protocol"],
                    namespace=namespace,
                )
            )
    return sorted(services, key=lambda x: (x.namespace, x.name, x.port))


def get_current_context() -> str:
    """Get the current kubectl context, extracting cluster name from ARN if present."""
    return parse_context(call_subprocess(["kubectl", "config", "current-context"]))


def get_available_namespaces() -> list[str]:
    """Get the list of available Kubernetes namespaces using kubectl."""
    return parse_namespaces(
        call_subprocess(["kubectl", "get", "namespaces", "-o", "json"])
    )


def get_services(namespace: str) -> list[KubernetesService]:
    """Get the list of services with their ports in the specified namespace."""
    return parse_services(
        call_subprocess(["kubectl", "get", "services", "-n", namespace, "-o", "json"]),
        namespace=namespace,
    )


def get_service(namespace: str, name: str) -> KubernetesService | None:
    """Look up a single service by name in the given namespace.

    Returns None when the service does not exist.
    Raises CalledProcessError on connectivity or auth errors.
    """
    raw = call_subprocess(
        [
            "kubectl",
            "get",
            "svc",
            "-n",
            namespace,
            "--field-selector",
            f"metadata.name={name}",
            "-o",
            "json",
        ]
    )
    services = parse_services(raw, namespace)
    return services[0] if services else None
