import base64
from types import SimpleNamespace

import pytest
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
    SecretKeyRef,
    SecretRef,
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
from kubek.kube.dto.kind import Kind
from kubek.kube.dto.secret import Secret as SecretDTO
from kubek.kube.dto.secret import SecretMetadata
from kubek.kube.dto.workflowtemplate.template import ContainerTemplate
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
        assert namespace is not None, "namespace must be provided"
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
