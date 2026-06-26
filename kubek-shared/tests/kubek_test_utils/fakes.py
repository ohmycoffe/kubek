import copy

from kubek.kube.config import ResolvedKubeConfig
from kubek.kube.dto.kind import Kind
from kubek.kube.errors import KubeApiNotFoundError


class FakeKubeClient:
    """Fake KubeClient that returns pre-configured raw dict responses."""

    def __init__(self) -> None:
        self._namespaced_responses = {}
        self._namespaces = {}

    @property
    def current_config(self) -> ResolvedKubeConfig:
        return ResolvedKubeConfig(
            context="test-context",
            namespace="test-ns",
            kubeconfig=None,
            skip_tls_verify=False,
        )

    def _get_one(self, resource: str, name: str, namespace: str | None = None) -> dict:
        if namespace is None:
            namespace = self.current_config.namespace
        try:
            return self._namespaced_responses[namespace][resource][name]
        except KeyError:
            raise KubeApiNotFoundError("not found") from None

    def _get_list(self, resource: str, namespace: str | None = None) -> dict:
        namespace = namespace or self.current_config.namespace
        try:
            return {
                "items": list(self._namespaced_responses[namespace][resource].values())
            }
        except KeyError:
            raise KubeApiNotFoundError("not found") from None

    async def get_deployment(self, name, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_one(Kind.DEPLOYMENT, name, namespace)

    async def get_deployments(self, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_list(Kind.DEPLOYMENT, namespace)

    async def get_statefulset(self, name, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_one(Kind.STATEFULSET, name, namespace)

    async def get_statefulsets(self, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_list(Kind.STATEFULSET, namespace)

    async def get_daemonset(self, name, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_one(Kind.DAEMONSET, name, namespace)

    async def get_daemonsets(self, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_list(Kind.DAEMONSET, namespace)

    async def get_replica_set(self, name, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_one(Kind.REPLICASET, name, namespace)

    async def get_replica_sets(self, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_list(Kind.REPLICASET, namespace)

    async def get_job(self, name, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_one(Kind.JOB, name, namespace)

    async def get_jobs(self, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_list(Kind.JOB, namespace)

    async def get_cronjob(self, name, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_one(Kind.CRONJOB, name, namespace)

    async def get_cronjobs(self, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_list(Kind.CRONJOB, namespace)

    async def get_secret(self, name, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_one(Kind.SECRET, name, namespace)

    async def get_secrets(self, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_list(Kind.SECRET, namespace)

    async def get_configmap(self, name, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_one(Kind.CONFIGMAP, name, namespace)

    async def get_configmaps(self, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_list(Kind.CONFIGMAP, namespace)

    async def get_workflowtemplate(self, name, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_one(Kind.WORKFLOWTEMPLATE, name, namespace)

    async def get_workflowtemplates(self, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_list(Kind.WORKFLOWTEMPLATE, namespace)

    async def get_service(self, name, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_one(Kind.SERVICE, name, namespace)

    async def get_services(self, namespace=None):
        namespace = namespace or self.current_config.namespace
        return self._get_list(Kind.SERVICE, namespace)

    async def get_namespace(self, name):
        try:
            return self._namespaces[name]
        except KeyError:
            raise KubeApiNotFoundError("not found") from None

    async def get_namespaces(self):
        return {"items": list(self._namespaces.values())}

    def add_namespaced_resource(
        self,
        kind: Kind,
        name: str,
        response: dict,
        namespace: str | None = None,
    ):
        namespace = namespace or self.current_config.namespace

        ns: dict = self._namespaced_responses.setdefault(namespace, {})
        res: dict = ns.setdefault(kind, {})

        res[name] = copy.deepcopy(response)
        return self

    def add_namespace(
        self,
        name: str,
        response: dict,
    ):
        if name not in self._namespaced_responses:
            self._namespaced_responses[name] = {}

        self._namespaces[name] = copy.deepcopy(response)
        return self
