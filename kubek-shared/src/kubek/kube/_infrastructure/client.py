from __future__ import annotations

import logging
from collections.abc import Callable
from functools import wraps
from http import HTTPStatus
from typing import Any, NoReturn, ParamSpec, Protocol, Self, TypeVar, cast

import urllib3.exceptions
from kubernetes import client
from kubernetes.config import (
    ConfigException,
    list_kube_config_contexts,
    load_kube_config,
)

from kubek.kube.config import KubeConfig, ResolvedKubeConfig
from kubek.kube.constants import DEFAULT_NAMESPACE
from kubek.kube.errors import (
    KubeAccessDeniedError,
    KubeApiNotFoundError,
    KubeAuthenticationError,
    KubeClientError,
    KubeConfigError,
)

logger = logging.getLogger(__name__)


class KubeSession:
    """Holds an isolated kubernetes Configuration + API stubs and the resolved config."""

    def __init__(
        self,
        *,
        core_v1: client.CoreV1Api,
        apps_v1: client.AppsV1Api,
        batch_v1: client.BatchV1Api,
        custom: client.CustomObjectsApi,
        current_config: ResolvedKubeConfig,
    ) -> None:
        self.core_v1 = core_v1
        self.apps_v1 = apps_v1
        self.batch_v1 = batch_v1
        self.custom = custom
        self.current_config = current_config

    @classmethod
    def from_config(cls, config: KubeConfig | None = None) -> Self:
        cfg = config or KubeConfig()
        configuration = client.Configuration()
        try:
            # Load configuration from kubeconfig file
            load_kube_config(
                config_file=cfg.kubeconfig,
                context=cfg.context,
                client_configuration=configuration,
            )
        except ConfigException as e:
            raise KubeConfigError(f"failed to load kubeconfig: {e}") from e

        api = client.ApiClient(configuration)
        return cls(
            core_v1=client.CoreV1Api(api),
            apps_v1=client.AppsV1Api(api),
            batch_v1=client.BatchV1Api(api),
            custom=client.CustomObjectsApi(api),
            current_config=cls.__resolve_config(cfg),
        )

    @staticmethod
    def __resolve_config(cfg: KubeConfig) -> ResolvedKubeConfig:
        _, active = list_kube_config_contexts(config_file=cfg.kubeconfig)
        if not active:
            raise KubeConfigError("no current context found in kubeconfig")

        ns = (
            cfg.namespace
            or active.get("context", {}).get("namespace")
            or DEFAULT_NAMESPACE
        )
        context = cfg.context or active["name"]
        return ResolvedKubeConfig(
            context=context,
            namespace=ns,
            kubeconfig=cfg.kubeconfig,
        )


class KubernetesResponseObject(Protocol):
    """Protocol for Kubernetes API response objects."""

    def to_dict(self) -> dict[str, Any]: ...


P = ParamSpec("P")

R = TypeVar("R")


def _raise_api_exception(e: client.ApiException) -> NoReturn:
    context = {
        "status": e.status,
        "reason": e.reason,
        "body": e.body,
    }
    logger.debug(str(e))
    if e.status == HTTPStatus.NOT_FOUND:
        raise KubeApiNotFoundError("resource not found", context=context) from e

    if e.status == HTTPStatus.UNAUTHORIZED:
        raise KubeAuthenticationError("access unauthorized", context=context) from e

    if e.status == HTTPStatus.FORBIDDEN:
        raise KubeAccessDeniedError("access forbidden", context=context) from e

    raise KubeClientError("client error", context=context) from e


def safe(fn: Callable[P, R]) -> Callable[P, R]:
    @wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            raw = fn(*args, **kwargs)
        except client.ApiException as e:
            _raise_api_exception(e)
        except urllib3.exceptions.MaxRetryError as e:
            match e.reason:
                case urllib3.exceptions.SSLError():
                    raise KubeClientError(
                        f"{e.reason}", context={"reason": str(e.reason)}
                    ) from e
            raise e
        return raw

    return wrapper


def as_dict(fn: Callable[P, Any]) -> Callable[P, dict[str, Any]]:
    @wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> dict[str, Any]:
        res = fn(*args, **kwargs)

        if hasattr(res, "to_dict"):
            return cast(
                dict[str, Any],
                cast(KubernetesResponseObject, res).to_dict(),
            )

        if isinstance(res, dict):
            return res

        raise TypeError(f"Expected dict-like response, got {type(res)}")

    return wrapper


class KubernetesClient:
    """Client for Kubernetes API"""

    __ARGO_WF_GROUP = "argoproj.io"
    __ARGO_WF_VERSION = "v1alpha1"
    __ARGO_WF_PLURAL = "workflowtemplates"

    def __init__(self, session: KubeSession) -> None:
        self.session: KubeSession = session

    @classmethod
    def from_config(cls, config: KubeConfig | None = None) -> Self:
        return cls(session=KubeSession.from_config(config))

    @property
    def current_config(self) -> ResolvedKubeConfig:
        return self.session.current_config

    @as_dict
    @safe
    def get_namespaces(self):
        """Get the list of available Kubernetes namespaces."""
        res = self.session.core_v1.list_namespace()
        return res

    @as_dict
    @safe
    def get_namespace(self, name: str):
        """Get a single namespace by name."""
        res = self.session.core_v1.read_namespace(name)
        return res

    @as_dict
    @safe
    def get_services(self, namespace: str | None = None):
        """Get services with their ports in the specified namespace."""
        ns = namespace or self.session.current_config.namespace
        res = self.session.core_v1.list_namespaced_service(ns)
        return res

    @as_dict
    @safe
    def get_service(self, name: str, namespace: str | None = None):
        """Look up a single service by name"""
        ns = namespace or self.session.current_config.namespace
        res = self.session.core_v1.read_namespaced_service(name, ns)
        return res

    @as_dict
    @safe
    def get_pods(self, namespace: str | None = None):
        """List pods in the specified namespace."""
        ns = namespace or self.session.current_config.namespace
        res = self.session.core_v1.list_namespaced_pod(ns)
        return res

    @as_dict
    @safe
    def get_pod(self, name: str, namespace: str | None = None):
        """Look up a single pod by name."""
        ns = namespace or self.session.current_config.namespace
        res = self.session.core_v1.read_namespaced_pod(name, ns)
        return res

    @as_dict
    @safe
    def get_deployments(self, namespace: str | None = None):
        """List deployment names in the specified namespace."""
        ns = namespace or self.session.current_config.namespace
        res = self.session.apps_v1.list_namespaced_deployment(ns)
        return res

    @as_dict
    @safe
    def get_deployment(self, name: str, namespace: str | None = None):
        """Get deployment by name in the specified namespace."""
        ns = namespace or self.session.current_config.namespace
        res = self.session.apps_v1.read_namespaced_deployment(name, ns)
        return res

    @as_dict
    @safe
    def get_statefulsets(self, namespace: str | None = None):
        """List statefulsets in the specified namespace."""
        ns = namespace or self.session.current_config.namespace
        res = self.session.apps_v1.list_namespaced_stateful_set(ns)
        return res

    @as_dict
    @safe
    def get_statefulset(self, name: str, namespace: str | None = None):
        """Get statefulset by name in the specified namespace."""
        ns = namespace or self.session.current_config.namespace
        res = self.session.apps_v1.read_namespaced_stateful_set(name, ns)
        return res

    @as_dict
    @safe
    def get_daemonsets(self, namespace: str | None = None):
        """List daemonsets in the specified namespace."""
        ns = namespace or self.session.current_config.namespace
        res = self.session.apps_v1.list_namespaced_daemon_set(ns)
        return res

    @as_dict
    @safe
    def get_daemonset(self, name: str, namespace: str | None = None):
        """Get daemonset by name in the specified namespace."""
        ns = namespace or self.session.current_config.namespace
        res = self.session.apps_v1.read_namespaced_daemon_set(name, ns)
        return res

    @as_dict
    @safe
    def get_replica_sets(self, namespace: str | None = None):
        """List replicasets in the specified namespace."""
        ns = namespace or self.session.current_config.namespace
        res = self.session.apps_v1.list_namespaced_replica_set(ns)
        return res

    @as_dict
    @safe
    def get_replica_set(self, name: str, namespace: str | None = None):
        """Get replicaset by name in the specified namespace."""
        ns = namespace or self.session.current_config.namespace
        res = self.session.apps_v1.read_namespaced_replica_set(name, ns)
        return res

    @as_dict
    @safe
    def get_jobs(self, namespace: str | None = None):
        """List jobs in the specified namespace."""
        ns = namespace or self.session.current_config.namespace
        res = self.session.batch_v1.list_namespaced_job(ns)
        return res

    @as_dict
    @safe
    def get_job(self, name: str, namespace: str | None = None):
        """Get job by name in the specified namespace."""
        ns = namespace or self.session.current_config.namespace
        res = self.session.batch_v1.read_namespaced_job(name, ns)
        return res

    @as_dict
    @safe
    def get_cronjobs(self, namespace: str | None = None):
        """List cronjobs in the specified namespace."""
        ns = namespace or self.session.current_config.namespace
        res = self.session.batch_v1.list_namespaced_cron_job(ns)
        return res

    @as_dict
    @safe
    def get_cronjob(self, name: str, namespace: str | None = None):
        """Get cronjob by name in the specified namespace."""
        ns = namespace or self.session.current_config.namespace
        res = self.session.batch_v1.read_namespaced_cron_job(name, ns)
        return res

    @as_dict
    @safe
    def get_secret(self, name: str, namespace: str | None = None):
        ns = namespace or self.session.current_config.namespace
        res = self.session.core_v1.read_namespaced_secret(name, ns)
        return res

    @as_dict
    @safe
    def get_secrets(self, namespace: str | None = None):
        ns = namespace or self.session.current_config.namespace
        res = self.session.core_v1.list_namespaced_secret(ns)
        return res

    @as_dict
    @safe
    def get_configmap(self, name: str, namespace: str | None = None):
        ns = namespace or self.session.current_config.namespace
        res = self.session.core_v1.read_namespaced_config_map(name, ns)
        return res

    @as_dict
    @safe
    def get_configmaps(self, namespace: str | None = None):
        ns = namespace or self.session.current_config.namespace
        res = self.session.core_v1.list_namespaced_config_map(ns)
        return res

    @as_dict
    @safe
    def get_workflowtemplates(self, namespace: str | None = None):
        ns = namespace or self.session.current_config.namespace
        res = self.session.custom.list_namespaced_custom_object(
            group=self.__ARGO_WF_GROUP,
            version=self.__ARGO_WF_VERSION,
            plural=self.__ARGO_WF_PLURAL,
            namespace=ns,
        )
        return res

    @as_dict
    @safe
    def get_workflowtemplate(self, name: str, namespace: str | None = None):
        ns = namespace or self.session.current_config.namespace
        res = self.session.custom.get_namespaced_custom_object(
            group=self.__ARGO_WF_GROUP,
            version=self.__ARGO_WF_VERSION,
            plural=self.__ARGO_WF_PLURAL,
            namespace=ns,
            name=name,
        )
        return res
