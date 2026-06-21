import json

import pytest
from conftest import RESOURCES_DIR
from kubek.kube._infrastructure.repositories.configmap import (
    KubernetesConfigMapRepository,
)
from kubek.kube._infrastructure.repositories.cronjob import (
    KubernetesCronJobRepository,
)
from kubek.kube._infrastructure.repositories.daemonset import (
    KubernetesDaemonSetRepository,
)
from kubek.kube._infrastructure.repositories.deployment import (
    KubernetesDeploymentRepository,
)
from kubek.kube._infrastructure.repositories.job import (
    KubernetesJobRepository,
)
from kubek.kube._infrastructure.repositories.namespace import (
    KubernetesNamespaceRepository,
)
from kubek.kube._infrastructure.repositories.replicaset import (
    KubernetesReplicaSetRepository,
)
from kubek.kube._infrastructure.repositories.secret import KubernetesSecretRepository
from kubek.kube._infrastructure.repositories.statefulset import (
    KubernetesStatefulSetRepository,
)
from kubek.kube._infrastructure.repositories.workflowtemplate import (
    KubernetesWorkflowTemplateRepository,
)
from kubek.kube.dto.kind import Kind
from kubek_test_utils.fakes import FakeKubeClient


def _strip_inline_comment(line: str) -> str:
    """Strip inline comments from JSON lines."""
    in_string = False
    escaped = False

    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue

        if char == "\\":
            escaped = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if not in_string and line[index : index + 2] == "//":
            return line[:index].rstrip()

    return line


def _load_json(filename: str) -> list[dict]:
    """Load JSON file from resources directory, stripping inline comments."""
    path = RESOURCES_DIR / "k8s" / "api-responses" / filename
    content = path.read_text()
    cleaned_content = "\n".join(
        _strip_inline_comment(line) for line in content.splitlines()
    )
    return json.loads(cleaned_content)


@pytest.fixture
def real_data_client():
    """Fixture that loads real API responses from JSON and populates FakeKubeClient."""
    client = FakeKubeClient()

    # Add deployments
    for item in _load_json("Deployment.json"):
        ns = item["metadata"]["namespace"]
        name = item["metadata"]["name"]
        client.add_namespaced_resource(Kind.DEPLOYMENT, name, item, namespace=ns)

    # Add statefulsets
    for item in _load_json("StatefulSet.json"):
        ns = item["metadata"]["namespace"]
        name = item["metadata"]["name"]
        client.add_namespaced_resource(Kind.STATEFULSET, name, item, namespace=ns)

    # Add daemonsets
    for item in _load_json("DaemonSet.json"):
        ns = item["metadata"]["namespace"]
        name = item["metadata"]["name"]
        client.add_namespaced_resource(Kind.DAEMONSET, name, item, namespace=ns)

    # Add replicasets
    for item in _load_json("ReplicaSet.json"):
        ns = item["metadata"]["namespace"]
        name = item["metadata"]["name"]
        client.add_namespaced_resource(Kind.REPLICASET, name, item, namespace=ns)

    # Add jobs
    for item in _load_json("Job.json"):
        ns = item["metadata"]["namespace"]
        name = item["metadata"]["name"]
        client.add_namespaced_resource(Kind.JOB, name, item, namespace=ns)

    # Add cronjobs
    for item in _load_json("CronJob.json"):
        ns = item["metadata"]["namespace"]
        name = item["metadata"]["name"]
        client.add_namespaced_resource(Kind.CRONJOB, name, item, namespace=ns)

    # Add services
    for item in _load_json("Service.json"):
        ns = item["metadata"]["namespace"]
        name = item["metadata"]["name"]
        client.add_namespaced_resource(Kind.SERVICE, name, item, namespace=ns)

    # Add secrets
    for item in _load_json("Secret.json"):
        ns = item["metadata"]["namespace"]
        name = item["metadata"]["name"]
        client.add_namespaced_resource(Kind.SECRET, name, item, namespace=ns)

    # Add configmaps
    for item in _load_json("ConfigMap.json"):
        ns = item["metadata"]["namespace"]
        name = item["metadata"]["name"]
        client.add_namespaced_resource(Kind.CONFIGMAP, name, item, namespace=ns)

    # Add workflow templates
    for item in _load_json("WorkflowTemplate.json"):
        ns = item["metadata"]["namespace"]
        name = item["metadata"]["name"]
        client.add_namespaced_resource(Kind.WORKFLOWTEMPLATE, name, item, namespace=ns)

    # Add namespaces
    for item in _load_json("Namespace.json"):
        name = item["metadata"]["name"]
        client.add_namespace(name, item)

    return client


class TestRepositoriesWithRealData:
    NS = "ns-kubek-shared"

    def test_deployment_names(self, real_data_client):
        repo = KubernetesDeploymentRepository(real_data_client)
        result = repo.list(namespace=self.NS)

        assert {d.metadata.name for d in result} == {
            "api-service",
            "dummy-service",
        }

    def test_deployment_env_parsing(self, real_data_client):
        repo = KubernetesDeploymentRepository(real_data_client)
        result = repo.list(namespace=self.NS)

        api = next(d for d in result if d.metadata.name == "api-service")
        container = api.spec.template.spec.containers[0]

        assert container.env_from
        assert any(e.config_map_ref for e in container.env_from)
        assert any(e.secret_ref for e in container.env_from)

        assert container.env
        assert any(e.name == "DB_PASSWORD" for e in container.env)
        assert any(e.name == "DIRECT_VALUE" for e in container.env)

    def test_statefulset_names(self, real_data_client):
        repo = KubernetesStatefulSetRepository(real_data_client)
        result = repo.list(namespace=self.NS)

        assert {s.metadata.name for s in result} == {
            "cache-service",
            "dummy-statefulset",
        }

    def test_statefulset_env_parsing(self, real_data_client):
        repo = KubernetesStatefulSetRepository(real_data_client)
        result = repo.list(namespace=self.NS)

        cache = next(s for s in result if s.metadata.name == "cache-service")
        container = cache.spec.template.spec.containers[0]

        assert container.env_from
        assert any(e.config_map_ref for e in container.env_from)
        assert any(e.secret_ref for e in container.env_from)

        assert container.env
        assert any(e.name == "DB_PASSWORD" for e in container.env)
        assert any(e.name == "DIRECT_VALUE" for e in container.env)

    def test_daemonset_names(self, real_data_client):
        repo = KubernetesDaemonSetRepository(real_data_client)
        result = repo.list(namespace=self.NS)

        assert {d.metadata.name for d in result} == {
            "log-agent",
            "dummy-daemonset",
        }

    def test_daemonset_env_parsing(self, real_data_client):
        repo = KubernetesDaemonSetRepository(real_data_client)
        result = repo.list(namespace=self.NS)

        agent = next(d for d in result if d.metadata.name == "log-agent")
        container = agent.spec.template.spec.containers[0]

        assert container.env_from
        assert any(e.config_map_ref for e in container.env_from)
        assert any(e.secret_ref for e in container.env_from)

        assert container.env
        assert any(e.name == "DB_PASSWORD" for e in container.env)
        assert any(e.name == "DIRECT_VALUE" for e in container.env)

    def test_replicaset_names(self, real_data_client):
        repo = KubernetesReplicaSetRepository(real_data_client)
        result = repo.list(namespace=self.NS)

        assert {r.metadata.name for r in result} == {
            "log-agent-rs",
            "dummy-replicaset",
        }

    def test_replicaset_env_parsing(self, real_data_client):
        repo = KubernetesReplicaSetRepository(real_data_client)
        result = repo.list(namespace=self.NS)

        agent = next(r for r in result if r.metadata.name == "log-agent-rs")
        container = agent.spec.template.spec.containers[0]

        assert container.env_from
        assert any(e.config_map_ref for e in container.env_from)
        assert any(e.secret_ref for e in container.env_from)

        assert container.env
        assert any(e.name == "DB_PASSWORD" for e in container.env)
        assert any(e.name == "DIRECT_VALUE" for e in container.env)

    def test_job_names(self, real_data_client):
        repo = KubernetesJobRepository(real_data_client)
        result = repo.list(namespace=self.NS)

        assert {j.metadata.name for j in result} == {
            "data-migration",
            "dummy-job",
        }

    def test_job_env_parsing(self, real_data_client):
        repo = KubernetesJobRepository(real_data_client)
        result = repo.list(namespace=self.NS)

        migration = next(j for j in result if j.metadata.name == "data-migration")
        container = migration.spec.template.spec.containers[0]

        assert container.env_from
        assert any(e.config_map_ref for e in container.env_from)
        assert any(e.secret_ref for e in container.env_from)

        assert container.env
        assert any(e.name == "DB_PASSWORD" for e in container.env)
        assert any(e.name == "DIRECT_VALUE" for e in container.env)

    def test_cronjob_names(self, real_data_client):
        repo = KubernetesCronJobRepository(real_data_client)
        result = repo.list(namespace=self.NS)

        assert {c.metadata.name for c in result} == {
            "nightly-backup",
            "dummy-cronjob",
        }

    def test_cronjob_env_parsing(self, real_data_client):
        repo = KubernetesCronJobRepository(real_data_client)
        result = repo.list(namespace=self.NS)

        backup = next(c for c in result if c.metadata.name == "nightly-backup")
        container = backup.spec.job_template.spec.template.spec.containers[0]

        assert container.env_from
        assert any(e.config_map_ref for e in container.env_from)
        assert any(e.secret_ref for e in container.env_from)

        assert container.env
        assert any(e.name == "DB_PASSWORD" for e in container.env)
        assert any(e.name == "DIRECT_VALUE" for e in container.env)

    def test_secret_decoding(self, real_data_client):
        repo = KubernetesSecretRepository(real_data_client)
        result = repo.list(namespace=self.NS)

        s = next(s for s in result if s.metadata.name == "app-secrets")
        assert s.decoded("API_KEY") == "myapikey123"

    def test_configmap_data(self, real_data_client):
        repo = KubernetesConfigMapRepository(real_data_client)
        result = repo.list(namespace=self.NS)

        c = next(c for c in result if c.metadata.name == "app-config")
        assert c.data["APP_ENV"] == "local"

    def test_workflow_names(self, real_data_client):
        repo = KubernetesWorkflowTemplateRepository(real_data_client)
        result = repo.list(namespace=self.NS)

        assert {w.metadata.name for w in result} == {
            "data-processor",
            "dummy-worker",
        }

    def test_namespace_list(self, real_data_client):
        repo = KubernetesNamespaceRepository(real_data_client)

        names = {n.metadata.name for n in repo.list()}
        assert self.NS in names
