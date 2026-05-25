import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kubek.kube import Deployment, Namespace, Secret, Service
from kubek.kube.api import KubeFacade
from kubek.kube.config import ResolvedKubeConfig
from kubek.kube.dto.configmap import ConfigMap
from kubek.kube.dto.kind import Kind
from kubek.kube.dto.workflowtemplate.workflowtemplate import WorkflowTemplate

RESOURCES_DIR = Path(__file__).parent.parent / "resources"


mapping = {
    Kind.DEPLOYMENT: Deployment,
    Kind.SERVICE: Service,
    Kind.SECRET: Secret,
    Kind.NAMESPACE: Namespace,
    Kind.WORKFLOWTEMPLATE: WorkflowTemplate,
    Kind.CONFIGMAP: ConfigMap,
}


@dataclass(frozen=True)
class FakeKubeResponses:
    deployment: list[Deployment]
    service: list[Service]
    secret: list[Secret]
    namespace: list[Namespace]
    workflowtemplate: list[WorkflowTemplate]
    configmap: list[ConfigMap]


def _strip_inline_comment(line: str) -> str:
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


def load_json_with_inline_comments(file_path: str) -> dict[str, Any]:
    with open(file_path, encoding="utf-8") as file:
        content = file.read()

    cleaned_content = "\n".join(
        _strip_inline_comment(line) for line in content.splitlines()
    )

    return json.loads(cleaned_content)


def _read_kube_responses(dir: Path = RESOURCES_DIR) -> FakeKubeResponses:
    raw = {}
    for resource in [
        Kind.DEPLOYMENT,
        Kind.SERVICE,
        Kind.SECRET,
        Kind.NAMESPACE,
        Kind.WORKFLOWTEMPLATE,
        Kind.CONFIGMAP,
    ]:
        with open(
            f"{dir}/k8s/api-responses/{resource.value}.json", encoding="utf-8"
        ) as f:
            content = f.read()
            cleaned_content = "\n".join(
                _strip_inline_comment(line) for line in content.splitlines()
            )
            raw[resource] = json.loads(cleaned_content)

    parsed = {}
    for k, v in raw.items():
        if k in mapping:
            parsed[k.lower()] = [mapping[k].model_validate(el) for el in v]
    return FakeKubeResponses(**parsed)


def create_fake_kube_facade():
    responses = _read_kube_responses()

    namespaces = {s.metadata.namespace for s in responses.deployment}
    assert len(namespaces) == 1, "Expected exactly one namespace in the responses"
    default_namespace = namespaces.pop()

    current_config = ResolvedKubeConfig(
        context="fake-context", namespace=default_namespace
    )

    class FakeRepository:
        def __init__(self, items: list):
            self._items = items
            self._default_namespace = default_namespace

        def list(self, namespace: str | None = None) -> list:
            namespace = namespace or self._default_namespace
            return [el for el in self._items if el.metadata.namespace == namespace]

        def get(self, name: str, namespace: str | None = None):
            namespace = namespace or self._default_namespace
            return next(
                (
                    el
                    for el in self._items
                    if el.metadata.name == name and el.metadata.namespace == namespace
                ),
                None,
            )

    class FakeNamespaceRepository:
        def list(self) -> list[Namespace]:
            return responses.namespace

        def get(self, name: str) -> Namespace | None:
            return next(
                (el for el in responses.namespace if el.metadata.name == name), None
            )

    deployment_repo = FakeRepository(responses.deployment)
    service_repo = FakeRepository(responses.service)
    secret_repo = FakeRepository(responses.secret)
    configmap_repo = FakeRepository(responses.configmap)
    workflowtemplate_repo = FakeRepository(responses.workflowtemplate)

    return KubeFacade(
        namespace=FakeNamespaceRepository(),
        deployment=deployment_repo,
        service=service_repo,
        workflowtemplate=workflowtemplate_repo,
        secret=secret_repo,
        configmap=configmap_repo,
        current_config=current_config,
    )
