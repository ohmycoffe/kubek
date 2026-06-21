import base64
from types import SimpleNamespace

import pytest
from export_dotenv.errors import (
    AmbiguousResourceError,
    ResourceNotFoundError,
    UnsupportedFormatError,
    UnsupportedKindError,
)
from export_dotenv.kube import (
    extract_envs_from_container,
    get_daemonset_envs,
    get_deployment_envs,
    get_job_envs,
    get_pod_envs,
    get_statefulset_envs,
    get_workflowtemplate_envs,
)
from export_dotenv.use_case import fetch_environment_values
from kubek.kube import ResolvedKubeConfig
from kubek.kube.dto.configmap import ConfigMap, ConfigMapMetadata
from kubek.kube.dto.container import (
    ConfigMapKeyRef,
    ConfigMapRef,
    Container,
    EnvFromSource,
    EnvValueFrom,
    EnvVar,
    FieldRef,
    ResourceFieldRef,
    SecretKeyRef,
    SecretRef,
)
from kubek.kube.dto.daemonset import (
    DaemonSet as DaemonSetDTO,
)
from kubek.kube.dto.daemonset import (
    DaemonSetMetadata,
    DaemonSetSpec,
)
from kubek.kube.dto.daemonset import (
    Template as DaemonSetTemplate,
)
from kubek.kube.dto.daemonset import (
    TemplateSpec as DaemonSetTemplateSpec,
)
from kubek.kube.dto.deployment import (
    Deployment as DeploymentDTO,
)
from kubek.kube.dto.deployment import (
    DeploymentMetadata,
    DeploymentSpec,
    Template,
    TemplateSpec,
)
from kubek.kube.dto.job import (
    Job as JobDTO,
)
from kubek.kube.dto.job import (
    JobMetadata,
    JobSpec,
)
from kubek.kube.dto.job import (
    Template as JobTemplate,
)
from kubek.kube.dto.job import (
    TemplateSpec as JobTemplateSpec,
)
from kubek.kube.dto.kind import Kind
from kubek.kube.dto.pod import Pod, PodMetadata, PodSpec
from kubek.kube.dto.secret import Secret as SecretDTO
from kubek.kube.dto.secret import SecretMetadata
from kubek.kube.dto.statefulset import (
    StatefulSet as StatefulSetDTO,
)
from kubek.kube.dto.statefulset import (
    StatefulSetMetadata,
    StatefulSetSpec,
)
from kubek.kube.dto.statefulset import (
    Template as StatefulSetTemplate,
)
from kubek.kube.dto.statefulset import (
    TemplateSpec as StatefulSetTemplateSpec,
)
from kubek.kube.dto.workflowtemplate.template import (
    ContainerTemplate,
    DagTemplate,
    Inputs,
    Parameters,
)
from kubek.kube.dto.workflowtemplate.workflowtemplate import (
    Metadata as WorkflowMetadata,
)
from kubek.kube.dto.workflowtemplate.workflowtemplate import (
    WorkflowSpec,
    WorkflowTemplate,
)

NS = "ns-kubectl-export-dotenv"


def b64(v: str) -> str:
    return base64.b64encode(v.encode()).decode()


class InMemoryRepository:
    def __init__(self, items):
        self.items = items

    def list(self, namespace: str | None = None):
        if namespace is None:
            return self.items
        return [x for x in self.items if x.metadata.namespace == namespace]

    def get(self, name: str, namespace: str | None = None):
        assert namespace is not None, "namespace must be provided"
        return next(
            (
                x
                for x in self.items
                if x.metadata.name == name and x.metadata.namespace == namespace
            ),
            None,
        )


def build_configmap():
    return ConfigMap(
        metadata=ConfigMapMetadata(name="app-config", namespace=NS),
        data={
            "APP_ENV": "local",
            "DATABASE_HOST": "postgres.demo.svc.cluster.local",
            "DATABASE_PORT": "5432",
            "FEATURE_FLAG_NEW_UI": "true",
            "LOG_LEVEL": "debug",
            "MAX_CONNECTIONS": "20",
            "SERVICE_TIMEOUT_MS": "3000",
        },
    )


def build_secret():
    return SecretDTO(
        metadata=SecretMetadata(name="app-secrets", namespace=NS),
        data={
            "API_KEY": b64("myapikey123"),
            "DATABASE_PASSWORD": b64("secretpassword"),
            "JWT_SECRET": b64("jwt-secret-token-xyz"),
            "REDIS_URL": b64("redis://redis.demo.svc.cluster.local:6379"),
            "S3_ACCESS_KEY": b64("s3-access-key-abc"),
        },
    )


def build_deployment():
    return DeploymentDTO(
        metadata=DeploymentMetadata(name="api-service", namespace=NS),
        spec=DeploymentSpec(
            template=Template(
                spec=TemplateSpec(
                    containers=[
                        Container(
                            env=[
                                EnvVar(
                                    name="DB_PASSWORD",
                                    value_from=EnvValueFrom(
                                        secret_key_ref=SecretKeyRef(
                                            name="app-secrets",
                                            key="DATABASE_PASSWORD",
                                        )
                                    ),
                                ),
                                EnvVar(
                                    name="LOG_LEVEL_OVERRIDE",
                                    value_from=EnvValueFrom(
                                        config_map_key_ref=ConfigMapKeyRef(
                                            name="app-config",
                                            key="LOG_LEVEL",
                                        )
                                    ),
                                ),
                                EnvVar(name="DIRECT_VALUE", value="hello-from-api"),
                                EnvVar(name="API_VERSION", value="v2"),
                                EnvVar(name="ENABLE_TRACING", value="true"),
                            ],
                            env_from=[
                                EnvFromSource(
                                    config_map_ref=ConfigMapRef(name="app-config")
                                ),
                                EnvFromSource(secret_ref=SecretRef(name="app-secrets")),
                            ],
                        )
                    ]
                )
            )
        ),
    )


def build_pod():
    return Pod(
        metadata=PodMetadata(name="api-pod", namespace=NS),
        spec=PodSpec(
            containers=[
                Container(
                    env=[
                        EnvVar(
                            name="DB_PASSWORD",
                            value_from=EnvValueFrom(
                                secret_key_ref=SecretKeyRef(
                                    name="app-secrets",
                                    key="DATABASE_PASSWORD",
                                )
                            ),
                        ),
                        EnvVar(
                            name="LOG_LEVEL_OVERRIDE",
                            value_from=EnvValueFrom(
                                config_map_key_ref=ConfigMapKeyRef(
                                    name="app-config",
                                    key="LOG_LEVEL",
                                )
                            ),
                        ),
                        EnvVar(name="DIRECT_VALUE", value="hello-from-api"),
                        EnvVar(name="API_VERSION", value="v2"),
                        EnvVar(name="ENABLE_TRACING", value="true"),
                    ],
                    env_from=[
                        EnvFromSource(config_map_ref=ConfigMapRef(name="app-config")),
                        EnvFromSource(secret_ref=SecretRef(name="app-secrets")),
                    ],
                )
            ]
        ),
    )


def build_statefulset():
    return StatefulSetDTO(
        metadata=StatefulSetMetadata(name="cache-service", namespace=NS),
        spec=StatefulSetSpec(
            template=StatefulSetTemplate(
                spec=StatefulSetTemplateSpec(
                    containers=[
                        Container(
                            env=[
                                EnvVar(
                                    name="DB_PASSWORD",
                                    value_from=EnvValueFrom(
                                        secret_key_ref=SecretKeyRef(
                                            name="app-secrets",
                                            key="DATABASE_PASSWORD",
                                        )
                                    ),
                                ),
                                EnvVar(name="DIRECT_VALUE", value="hello-from-cache"),
                            ],
                            env_from=[
                                EnvFromSource(
                                    config_map_ref=ConfigMapRef(name="app-config")
                                ),
                                EnvFromSource(secret_ref=SecretRef(name="app-secrets")),
                            ],
                        )
                    ]
                )
            )
        ),
    )


def build_daemonset():
    return DaemonSetDTO(
        metadata=DaemonSetMetadata(name="log-agent", namespace=NS),
        spec=DaemonSetSpec(
            template=DaemonSetTemplate(
                spec=DaemonSetTemplateSpec(
                    containers=[
                        Container(
                            env=[
                                EnvVar(
                                    name="DB_PASSWORD",
                                    value_from=EnvValueFrom(
                                        secret_key_ref=SecretKeyRef(
                                            name="app-secrets",
                                            key="DATABASE_PASSWORD",
                                        )
                                    ),
                                ),
                                EnvVar(name="DIRECT_VALUE", value="hello-from-agent"),
                            ],
                            env_from=[
                                EnvFromSource(
                                    config_map_ref=ConfigMapRef(name="app-config")
                                ),
                                EnvFromSource(secret_ref=SecretRef(name="app-secrets")),
                            ],
                        )
                    ]
                )
            )
        ),
    )


def build_job():
    return JobDTO(
        metadata=JobMetadata(name="data-migration", namespace=NS),
        spec=JobSpec(
            template=JobTemplate(
                spec=JobTemplateSpec(
                    containers=[
                        Container(
                            env=[
                                EnvVar(
                                    name="DB_PASSWORD",
                                    value_from=EnvValueFrom(
                                        secret_key_ref=SecretKeyRef(
                                            name="app-secrets",
                                            key="DATABASE_PASSWORD",
                                        )
                                    ),
                                ),
                                EnvVar(name="DIRECT_VALUE", value="hello-from-job"),
                            ],
                            env_from=[
                                EnvFromSource(
                                    config_map_ref=ConfigMapRef(name="app-config")
                                ),
                                EnvFromSource(secret_ref=SecretRef(name="app-secrets")),
                            ],
                        )
                    ]
                )
            )
        ),
    )


def build_workflow():
    return WorkflowTemplate(
        metadata=WorkflowMetadata(name="data-processor", namespace=NS),
        spec=WorkflowSpec(
            templates=[
                ContainerTemplate(
                    name="main",
                    container=Container(
                        env=[
                            EnvVar(
                                name="BATCH_SIZE",
                                value="{{inputs.parameters.batch_size}}",
                            ),
                            EnvVar(
                                name="SOURCE_BUCKET",
                                value="{{inputs.parameters.source_bucket}}",
                            ),
                            EnvVar(
                                name="DB_HOST",
                                value_from=EnvValueFrom(
                                    config_map_key_ref=ConfigMapKeyRef(
                                        name="app-config",
                                        key="DATABASE_HOST",
                                    )
                                ),
                            ),
                            EnvVar(
                                name="API_KEY",
                                value_from=EnvValueFrom(
                                    secret_key_ref=SecretKeyRef(
                                        name="app-secrets",
                                        key="API_KEY",
                                    )
                                ),
                            ),
                        ],
                        env_from=[
                            EnvFromSource(
                                config_map_ref=ConfigMapRef(name="app-config")
                            ),
                            EnvFromSource(secret_ref=SecretRef(name="app-secrets")),
                        ],
                    ),
                )
            ]
        ),
    )


@pytest.fixture
def api():
    return SimpleNamespace(
        deployment=InMemoryRepository([build_deployment()]),
        statefulset=InMemoryRepository([build_statefulset()]),
        daemonset=InMemoryRepository([build_daemonset()]),
        job=InMemoryRepository([build_job()]),
        pod=InMemoryRepository([build_pod()]),
        workflowtemplate=InMemoryRepository([build_workflow()]),
        secret=InMemoryRepository([build_secret()]),
        configmap=InMemoryRepository([build_configmap()]),
        current_config=ResolvedKubeConfig(context="test", namespace=NS),
    )


def test_workflowtemplate_env_vars(api):
    result = fetch_environment_values(
        kind=Kind.WORKFLOWTEMPLATE,
        name="data-processor",
        api=api,
    )

    assert result == {
        "APP_ENV": "local",
        "DATABASE_HOST": "postgres.demo.svc.cluster.local",
        "DATABASE_PORT": "5432",
        "FEATURE_FLAG_NEW_UI": "true",
        "LOG_LEVEL": "debug",
        "MAX_CONNECTIONS": "20",
        "SERVICE_TIMEOUT_MS": "3000",
        "API_KEY": "myapikey123",
        "DATABASE_PASSWORD": "secretpassword",
        "JWT_SECRET": "jwt-secret-token-xyz",
        "REDIS_URL": "redis://redis.demo.svc.cluster.local:6379",
        "S3_ACCESS_KEY": "s3-access-key-abc",
        "BATCH_SIZE": "{{inputs.parameters.batch_size}}",
        "SOURCE_BUCKET": "{{inputs.parameters.source_bucket}}",
        "DB_HOST": "postgres.demo.svc.cluster.local",
    }


def test_deployment_env_vars(api):
    result = fetch_environment_values(
        kind=Kind.DEPLOYMENT,
        name="api-service",
        api=api,
    )

    assert result == {
        "APP_ENV": "local",
        "DATABASE_HOST": "postgres.demo.svc.cluster.local",
        "DATABASE_PORT": "5432",
        "FEATURE_FLAG_NEW_UI": "true",
        "LOG_LEVEL": "debug",
        "MAX_CONNECTIONS": "20",
        "SERVICE_TIMEOUT_MS": "3000",
        "API_KEY": "myapikey123",
        "DATABASE_PASSWORD": "secretpassword",
        "JWT_SECRET": "jwt-secret-token-xyz",
        "REDIS_URL": "redis://redis.demo.svc.cluster.local:6379",
        "S3_ACCESS_KEY": "s3-access-key-abc",
        "DB_PASSWORD": "secretpassword",
        "LOG_LEVEL_OVERRIDE": "debug",
        "DIRECT_VALUE": "hello-from-api",
        "API_VERSION": "v2",
        "ENABLE_TRACING": "true",
    }


def test_statefulset_env_vars(api):
    """A single-container StatefulSet resolves env, envFrom, and value refs like a Deployment."""
    result = fetch_environment_values(
        kind=Kind.STATEFULSET,
        name="cache-service",
        api=api,
    )

    assert result == {
        "APP_ENV": "local",
        "DATABASE_HOST": "postgres.demo.svc.cluster.local",
        "DATABASE_PORT": "5432",
        "FEATURE_FLAG_NEW_UI": "true",
        "LOG_LEVEL": "debug",
        "MAX_CONNECTIONS": "20",
        "SERVICE_TIMEOUT_MS": "3000",
        "API_KEY": "myapikey123",
        "DATABASE_PASSWORD": "secretpassword",
        "JWT_SECRET": "jwt-secret-token-xyz",
        "REDIS_URL": "redis://redis.demo.svc.cluster.local:6379",
        "S3_ACCESS_KEY": "s3-access-key-abc",
        "DB_PASSWORD": "secretpassword",
        "DIRECT_VALUE": "hello-from-cache",
    }


def test_statefulset_not_found_raises(api):
    """A missing StatefulSet name raises ResourceNotFoundError."""
    with pytest.raises(ResourceNotFoundError, match="StatefulSet missing"):
        get_statefulset_envs(name="missing", api=api)


def test_statefulset_with_multiple_containers_raises(api):
    """A StatefulSet with more than one container is rejected as ambiguous."""
    api.statefulset = InMemoryRepository(
        [
            StatefulSetDTO(
                metadata=StatefulSetMetadata(name="cache-service", namespace=NS),
                spec=StatefulSetSpec(
                    template=StatefulSetTemplate(
                        spec=StatefulSetTemplateSpec(
                            containers=[Container(), Container()]
                        )
                    )
                ),
            )
        ]
    )

    with pytest.raises(AmbiguousResourceError, match="2 containers"):
        get_statefulset_envs(name="cache-service", api=api)


def test_daemonset_env_vars(api):
    """A single-container DaemonSet resolves env, envFrom, and value refs like a Deployment."""
    result = fetch_environment_values(
        kind=Kind.DAEMONSET,
        name="log-agent",
        api=api,
    )

    assert result == {
        "APP_ENV": "local",
        "DATABASE_HOST": "postgres.demo.svc.cluster.local",
        "DATABASE_PORT": "5432",
        "FEATURE_FLAG_NEW_UI": "true",
        "LOG_LEVEL": "debug",
        "MAX_CONNECTIONS": "20",
        "SERVICE_TIMEOUT_MS": "3000",
        "API_KEY": "myapikey123",
        "DATABASE_PASSWORD": "secretpassword",
        "JWT_SECRET": "jwt-secret-token-xyz",
        "REDIS_URL": "redis://redis.demo.svc.cluster.local:6379",
        "S3_ACCESS_KEY": "s3-access-key-abc",
        "DB_PASSWORD": "secretpassword",
        "DIRECT_VALUE": "hello-from-agent",
    }


def test_daemonset_not_found_raises(api):
    """A missing DaemonSet name raises ResourceNotFoundError."""
    with pytest.raises(ResourceNotFoundError, match="DaemonSet missing"):
        get_daemonset_envs(name="missing", api=api)


def test_daemonset_with_multiple_containers_raises(api):
    """A DaemonSet with more than one container is rejected as ambiguous."""
    api.daemonset = InMemoryRepository(
        [
            DaemonSetDTO(
                metadata=DaemonSetMetadata(name="log-agent", namespace=NS),
                spec=DaemonSetSpec(
                    template=DaemonSetTemplate(
                        spec=DaemonSetTemplateSpec(
                            containers=[Container(), Container()]
                        )
                    )
                ),
            )
        ]
    )

    with pytest.raises(AmbiguousResourceError, match="2 containers"):
        get_daemonset_envs(name="log-agent", api=api)


def test_job_env_vars(api):
    """A single-container Job resolves env, envFrom, and value refs like a Deployment."""
    result = fetch_environment_values(
        kind=Kind.JOB,
        name="data-migration",
        api=api,
    )

    assert result == {
        "APP_ENV": "local",
        "DATABASE_HOST": "postgres.demo.svc.cluster.local",
        "DATABASE_PORT": "5432",
        "FEATURE_FLAG_NEW_UI": "true",
        "LOG_LEVEL": "debug",
        "MAX_CONNECTIONS": "20",
        "SERVICE_TIMEOUT_MS": "3000",
        "API_KEY": "myapikey123",
        "DATABASE_PASSWORD": "secretpassword",
        "JWT_SECRET": "jwt-secret-token-xyz",
        "REDIS_URL": "redis://redis.demo.svc.cluster.local:6379",
        "S3_ACCESS_KEY": "s3-access-key-abc",
        "DB_PASSWORD": "secretpassword",
        "DIRECT_VALUE": "hello-from-job",
    }


def test_job_not_found_raises(api):
    """A missing Job name raises ResourceNotFoundError."""
    with pytest.raises(ResourceNotFoundError, match="Job missing"):
        get_job_envs(name="missing", api=api)


def test_job_with_multiple_containers_raises(api):
    """A Job with more than one container is rejected as ambiguous."""
    api.job = InMemoryRepository(
        [
            JobDTO(
                metadata=JobMetadata(name="data-migration", namespace=NS),
                spec=JobSpec(
                    template=JobTemplate(
                        spec=JobTemplateSpec(containers=[Container(), Container()])
                    )
                ),
            )
        ]
    )

    with pytest.raises(AmbiguousResourceError, match="2 containers"):
        get_job_envs(name="data-migration", api=api)


def test_pod_env_vars(api):
    result = fetch_environment_values(
        kind=Kind.POD,
        name="api-pod",
        api=api,
    )

    assert result == {
        "APP_ENV": "local",
        "DATABASE_HOST": "postgres.demo.svc.cluster.local",
        "DATABASE_PORT": "5432",
        "FEATURE_FLAG_NEW_UI": "true",
        "LOG_LEVEL": "debug",
        "MAX_CONNECTIONS": "20",
        "SERVICE_TIMEOUT_MS": "3000",
        "API_KEY": "myapikey123",
        "DATABASE_PASSWORD": "secretpassword",
        "JWT_SECRET": "jwt-secret-token-xyz",
        "REDIS_URL": "redis://redis.demo.svc.cluster.local:6379",
        "S3_ACCESS_KEY": "s3-access-key-abc",
        "DB_PASSWORD": "secretpassword",
        "LOG_LEVEL_OVERRIDE": "debug",
        "DIRECT_VALUE": "hello-from-api",
        "API_VERSION": "v2",
        "ENABLE_TRACING": "true",
    }


def test_configmap_env_vars(api):
    result = fetch_environment_values(
        kind=Kind.CONFIGMAP,
        name="app-config",
        api=api,
    )
    assert result == {
        "APP_ENV": "local",
        "DATABASE_HOST": "postgres.demo.svc.cluster.local",
        "DATABASE_PORT": "5432",
        "FEATURE_FLAG_NEW_UI": "true",
        "LOG_LEVEL": "debug",
        "MAX_CONNECTIONS": "20",
        "SERVICE_TIMEOUT_MS": "3000",
    }


def test_secret_env_vars(api):
    result = fetch_environment_values(
        kind=Kind.SECRET,
        name="app-secrets",
        api=api,
    )
    assert result == {
        "API_KEY": "myapikey123",
        "DATABASE_PASSWORD": "secretpassword",
        "JWT_SECRET": "jwt-secret-token-xyz",
        "REDIS_URL": "redis://redis.demo.svc.cluster.local:6379",
        "S3_ACCESS_KEY": "s3-access-key-abc",
    }


def test_deployment_not_found_raises(api):
    with pytest.raises(ResourceNotFoundError, match="Deployment missing"):
        get_deployment_envs(name="missing", api=api)


def test_deployment_with_multiple_containers_raises(api):
    api.deployment = InMemoryRepository(
        [
            DeploymentDTO(
                metadata=DeploymentMetadata(name="api-service", namespace=NS),
                spec=DeploymentSpec(
                    template=Template(
                        spec=TemplateSpec(containers=[Container(), Container()])
                    )
                ),
            )
        ]
    )

    with pytest.raises(AmbiguousResourceError, match="2 containers"):
        get_deployment_envs(name="api-service", api=api)


def test_pod_not_found_raises(api):
    with pytest.raises(ResourceNotFoundError, match="Pod missing"):
        get_pod_envs(name="missing", api=api)


def test_pod_with_multiple_containers_raises(api):
    api.pod = InMemoryRepository(
        [
            Pod(
                metadata=PodMetadata(name="api-pod", namespace=NS),
                spec=PodSpec(containers=[Container(), Container()]),
            )
        ]
    )

    with pytest.raises(AmbiguousResourceError, match="2 containers"):
        get_pod_envs(name="api-pod", api=api)


def test_missing_configmap_in_env_from_is_skipped(api):
    container = Container(
        env_from=[EnvFromSource(config_map_ref=ConfigMapRef(name="missing-config"))],
    )

    assert extract_envs_from_container(api=api, container=container) == {}


def test_missing_secret_in_env_from_is_skipped(api):
    container = Container(
        env_from=[EnvFromSource(secret_ref=SecretRef(name="missing-secret"))],
    )

    assert extract_envs_from_container(api=api, container=container) == {}


def test_unsupported_env_from_raises(api):
    container = Container(env_from=[EnvFromSource()])

    with pytest.raises(UnsupportedFormatError, match="Unknown envFrom"):
        extract_envs_from_container(api=api, container=container)


def test_missing_configmap_key_sets_empty_value(api):
    container = Container(
        env=[
            EnvVar(
                name="MISSING_KEY",
                value_from=EnvValueFrom(
                    config_map_key_ref=ConfigMapKeyRef(
                        name="app-config",
                        key="NOT_IN_CONFIGMAP",
                    )
                ),
            )
        ]
    )

    result = extract_envs_from_container(api=api, container=container)
    assert result == {"MISSING_KEY": ""}


def test_missing_secret_key_sets_empty_value(api):
    container = Container(
        env=[
            EnvVar(
                name="MISSING_KEY",
                value_from=EnvValueFrom(
                    secret_key_ref=SecretKeyRef(
                        name="app-secrets",
                        key="NOT_IN_SECRET",
                    )
                ),
            )
        ]
    )

    result = extract_envs_from_container(api=api, container=container)
    assert result == {"MISSING_KEY": ""}


def test_env_with_unknown_value_from_is_skipped(api):
    container = Container(
        env=[EnvVar(name="UNKNOWN", value_from=EnvValueFrom())],
    )

    assert extract_envs_from_container(api=api, container=container) == {}


def test_env_with_no_value_or_value_from_is_skipped(api):
    container = Container(env=[EnvVar(name="EMPTY")])

    assert extract_envs_from_container(api=api, container=container) == {}


def test_field_ref_is_skipped_silently(api, caplog):
    """Downward API fieldRef env vars resolve at pod runtime, so they are skipped without a warning."""
    container = Container(
        env=[
            EnvVar(
                name="MY_POD_NAME",
                value_from=EnvValueFrom(field_ref=FieldRef(field_path="metadata.name")),
            ),
            EnvVar(
                name="MY_POD_NAMESPACE",
                value_from=EnvValueFrom(
                    field_ref=FieldRef(field_path="metadata.namespace")
                ),
            ),
        ]
    )

    with caplog.at_level("WARNING"):
        result = extract_envs_from_container(api=api, container=container)

    assert result == {}
    assert caplog.records == []


def test_resource_field_ref_is_skipped_silently(api, caplog):
    """Downward API resourceFieldRef env vars are skipped without a warning."""
    container = Container(
        env=[
            EnvVar(
                name="CPU_LIMIT",
                value_from=EnvValueFrom(
                    resource_field_ref=ResourceFieldRef(
                        container_name="app", resource="limits.cpu"
                    )
                ),
            )
        ]
    )

    with caplog.at_level("WARNING"):
        result = extract_envs_from_container(api=api, container=container)

    assert result == {}
    assert caplog.records == []


def test_statefulset_skips_field_ref_env(api):
    """get_statefulset_envs skips fieldRef env vars while still emitting resolvable ones."""
    api.statefulset = InMemoryRepository(
        [
            StatefulSetDTO(
                metadata=StatefulSetMetadata(name="cache-service", namespace=NS),
                spec=StatefulSetSpec(
                    template=StatefulSetTemplate(
                        spec=StatefulSetTemplateSpec(
                            containers=[
                                Container(
                                    env=[
                                        EnvVar(
                                            name="MY_POD_NAME",
                                            value_from=EnvValueFrom(
                                                field_ref=FieldRef(
                                                    field_path="metadata.name"
                                                )
                                            ),
                                        ),
                                        EnvVar(
                                            name="DIRECT_VALUE",
                                            value="hello",
                                        ),
                                    ]
                                )
                            ]
                        )
                    )
                ),
            )
        ]
    )

    result = get_statefulset_envs(name="cache-service", api=api)
    assert result == {"DIRECT_VALUE": "hello"}


def test_workflowtemplate_not_found_raises(api):
    with pytest.raises(ResourceNotFoundError, match="WorkflowTemplate missing"):
        get_workflowtemplate_envs(name="missing", api=api)


def test_workflowtemplate_skips_non_container_templates(api):
    workflow = WorkflowTemplate(
        metadata=WorkflowMetadata(name="mixed", namespace=NS),
        spec=WorkflowSpec(
            templates=[
                DagTemplate(name="dag-step"),
                ContainerTemplate(
                    name="main",
                    container=Container(
                        env=[EnvVar(name="ONLY", value="from-container")],
                    ),
                ),
            ]
        ),
    )
    api.workflowtemplate = InMemoryRepository([workflow])

    result = get_workflowtemplate_envs(name="mixed", api=api)
    assert result == {"ONLY": "from-container"}


def test_workflowtemplate_builds_fallback_keys_from_parameter_defaults(api):
    workflow = WorkflowTemplate(
        metadata=WorkflowMetadata(name="with-defaults", namespace=NS),
        spec=WorkflowSpec(
            templates=[
                ContainerTemplate(
                    name="main",
                    inputs=Inputs(
                        parameters=[Parameters(name="batch_size", default="100")]
                    ),
                    container=Container(
                        env=[
                            EnvVar(
                                name="BATCH",
                                value_from=EnvValueFrom(
                                    config_map_key_ref=ConfigMapKeyRef(
                                        name="app-config",
                                        key="{{inputs.parameters.batch_size}}",
                                    )
                                ),
                            )
                        ],
                    ),
                )
            ]
        ),
    )
    api.workflowtemplate = InMemoryRepository([workflow])

    result = get_workflowtemplate_envs(name="with-defaults", api=api)
    assert result == {"BATCH": ""}


def test_missing_configmap_for_value_from_is_skipped(api):
    container = Container(
        env=[
            EnvVar(
                name="MISSING_CM",
                value_from=EnvValueFrom(
                    config_map_key_ref=ConfigMapKeyRef(
                        name="missing-config",
                        key="ANY",
                    )
                ),
            )
        ]
    )

    assert extract_envs_from_container(api=api, container=container) == {}


def test_missing_secret_for_value_from_is_skipped(api):
    container = Container(
        env=[
            EnvVar(
                name="MISSING_SECRET",
                value_from=EnvValueFrom(
                    secret_key_ref=SecretKeyRef(
                        name="missing-secret",
                        key="ANY",
                    )
                ),
            )
        ]
    )

    assert extract_envs_from_container(api=api, container=container) == {}


def test_fetch_environment_values_raises_for_unsupported_kind(api):
    with pytest.raises(UnsupportedKindError, match="Unsupported kind"):
        fetch_environment_values(kind=Kind.SERVICE, name="any", api=api)
