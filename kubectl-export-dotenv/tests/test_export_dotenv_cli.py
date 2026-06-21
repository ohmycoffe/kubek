from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from export_dotenv.cli import _print_kubeconfig, _select_resource_name
from export_dotenv.errors import NoResourcesFoundError
from export_dotenv.prompts import ask_for_kind, ask_for_resource
from kubek.kube import Kind, ResolvedKubeConfig
from kubek.kube.dto.container import Container
from kubek.kube.dto.cronjob import (
    CronJob,
    CronJobJobSpec,
    CronJobMetadata,
    CronJobSpec,
)
from kubek.kube.dto.cronjob import (
    JobTemplate as CronJobJobTemplate,
)
from kubek.kube.dto.cronjob import (
    Template as CronJobPodTemplate,
)
from kubek.kube.dto.cronjob import (
    TemplateSpec as CronJobPodTemplateSpec,
)
from kubek.kube.dto.daemonset import (
    DaemonSet,
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
    Deployment,
    DeploymentMetadata,
    DeploymentSpec,
    Template,
    TemplateSpec,
)
from kubek.kube.dto.job import (
    Job,
    JobMetadata,
    JobSpec,
)
from kubek.kube.dto.job import (
    Template as JobTemplate,
)
from kubek.kube.dto.job import (
    TemplateSpec as JobTemplateSpec,
)
from kubek.kube.dto.statefulset import (
    StatefulSet,
    StatefulSetMetadata,
    StatefulSetSpec,
)
from kubek.kube.dto.statefulset import (
    Template as StatefulSetTemplate,
)
from kubek.kube.dto.statefulset import (
    TemplateSpec as StatefulSetTemplateSpec,
)
from kubek.kube.dto.workflowtemplate.template import ContainerTemplate
from kubek.kube.dto.workflowtemplate.workflowtemplate import (
    Metadata as WorkflowMetadata,
)
from kubek.kube.dto.workflowtemplate.workflowtemplate import (
    WorkflowSpec,
    WorkflowTemplate,
)
from kubek.term.output import create_output

NS = "ns-kubectl-export-dotenv"


class _InMemoryRepository:
    def __init__(self, items):
        self.items = items

    def list(self, namespace: str | None = None):
        if namespace is None:
            return self.items
        return [x for x in self.items if x.metadata.namespace == namespace]


def _build_deployment() -> Deployment:
    return Deployment(
        metadata=DeploymentMetadata(name="api-service", namespace=NS),
        spec=DeploymentSpec(template=Template(spec=TemplateSpec(containers=[]))),
    )


def _build_statefulset() -> StatefulSet:
    return StatefulSet(
        metadata=StatefulSetMetadata(name="cache-service", namespace=NS),
        spec=StatefulSetSpec(
            template=StatefulSetTemplate(spec=StatefulSetTemplateSpec(containers=[]))
        ),
    )


def _build_daemonset() -> DaemonSet:
    return DaemonSet(
        metadata=DaemonSetMetadata(name="log-agent", namespace=NS),
        spec=DaemonSetSpec(
            template=DaemonSetTemplate(spec=DaemonSetTemplateSpec(containers=[]))
        ),
    )


def _build_job() -> Job:
    return Job(
        metadata=JobMetadata(name="data-migration", namespace=NS),
        spec=JobSpec(template=JobTemplate(spec=JobTemplateSpec(containers=[]))),
    )


def _build_cronjob() -> CronJob:
    return CronJob(
        metadata=CronJobMetadata(name="nightly-backup", namespace=NS),
        spec=CronJobSpec(
            job_template=CronJobJobTemplate(
                spec=CronJobJobSpec(
                    template=CronJobPodTemplate(
                        spec=CronJobPodTemplateSpec(containers=[])
                    )
                )
            )
        ),
    )


def _create_api(
    *,
    deployments: list[Deployment] | None = None,
    statefulsets: list[StatefulSet] | None = None,
    daemonsets: list[DaemonSet] | None = None,
    jobs: list[Job] | None = None,
    cronjobs: list[CronJob] | None = None,
):
    if deployments is None:
        deployments = [_build_deployment()]
    return SimpleNamespace(
        deployment=_InMemoryRepository(deployments),
        statefulset=_InMemoryRepository(statefulsets or []),
        daemonset=_InMemoryRepository(daemonsets or []),
        job=_InMemoryRepository(jobs or []),
        cronjob=_InMemoryRepository(cronjobs or []),
        workflowtemplate=_InMemoryRepository([]),
        current_config=ResolvedKubeConfig(context="test", namespace=NS),
    )


def test_ask_for_kind_delegates_to_questionary(monkeypatch):
    asked = []

    class FakeSelect:
        def __init__(self, *args, **kwargs):
            asked.append(kwargs.get("choices"))

        def ask(self):
            return Kind.DEPLOYMENT

    monkeypatch.setattr("export_dotenv.prompts.questionary.select", FakeSelect)

    assert ask_for_kind() == Kind.DEPLOYMENT
    assert asked


def test_ask_for_resource_delegates_to_questionary(monkeypatch):
    asked = []

    class FakeSelect:
        def __init__(self, *args, **kwargs):
            asked.append(kwargs.get("choices"))

        def ask(self):
            return "api-service"

    monkeypatch.setattr("export_dotenv.prompts.questionary.select", FakeSelect)

    assert ask_for_resource(["api-service"], Kind.DEPLOYMENT) == "api-service"
    assert asked == [["api-service"]]


def test_select_resource_name_returns_prompted_deployment():
    api = _create_api()

    with patch(
        "export_dotenv.cli.ask_for_resource",
        return_value="api-service",
    ) as ask:
        name = _select_resource_name(
            out=create_output(),
            kind=Kind.DEPLOYMENT,
            api=api,
        )

    assert name == "api-service"
    ask.assert_called_once()


def test_select_resource_name_raises_when_no_deployments():
    api = _create_api(deployments=[])

    with pytest.raises(NoResourcesFoundError, match="No Deployments found"):
        _select_resource_name(
            out=create_output(),
            kind=Kind.DEPLOYMENT,
            api=api,
        )


def test_select_resource_name_lists_workflowtemplates():
    workflow = WorkflowTemplate(
        metadata=WorkflowMetadata(name="data-processor", namespace=NS),
        spec=WorkflowSpec(
            templates=[
                ContainerTemplate(name="main", container=Container()),
            ]
        ),
    )
    api = _create_api(deployments=[])
    api.workflowtemplate = _InMemoryRepository([workflow])

    with patch(
        "export_dotenv.cli.ask_for_resource",
        return_value="data-processor",
    ) as ask:
        name = _select_resource_name(
            out=create_output(),
            kind=Kind.WORKFLOWTEMPLATE,
            api=api,
        )

    assert name == "data-processor"
    ask.assert_called_once_with(
        resources=["data-processor"],
        kind=Kind.WORKFLOWTEMPLATE,
    )


def test_select_resource_name_lists_statefulsets():
    """_select_resource_name lists StatefulSets from the statefulset repo for the StatefulSet kind."""
    api = _create_api(deployments=[], statefulsets=[_build_statefulset()])

    with patch(
        "export_dotenv.cli.ask_for_resource",
        return_value="cache-service",
    ) as ask:
        name = _select_resource_name(
            out=create_output(),
            kind=Kind.STATEFULSET,
            api=api,
        )

    assert name == "cache-service"
    ask.assert_called_once_with(
        resources=["cache-service"],
        kind=Kind.STATEFULSET,
    )


def test_select_resource_name_lists_daemonsets():
    """_select_resource_name lists DaemonSets from the daemonset repo for the DaemonSet kind."""
    api = _create_api(deployments=[], daemonsets=[_build_daemonset()])

    with patch(
        "export_dotenv.cli.ask_for_resource",
        return_value="log-agent",
    ) as ask:
        name = _select_resource_name(
            out=create_output(),
            kind=Kind.DAEMONSET,
            api=api,
        )

    assert name == "log-agent"
    ask.assert_called_once_with(
        resources=["log-agent"],
        kind=Kind.DAEMONSET,
    )


def test_select_resource_name_lists_jobs():
    """_select_resource_name lists Jobs from the job repo for the Job kind."""
    api = _create_api(deployments=[], jobs=[_build_job()])

    with patch(
        "export_dotenv.cli.ask_for_resource",
        return_value="data-migration",
    ) as ask:
        name = _select_resource_name(
            out=create_output(),
            kind=Kind.JOB,
            api=api,
        )

    assert name == "data-migration"
    ask.assert_called_once_with(
        resources=["data-migration"],
        kind=Kind.JOB,
    )


def test_select_resource_name_lists_cronjobs():
    """_select_resource_name lists CronJobs from the cronjob repo for the CronJob kind."""
    api = _create_api(deployments=[], cronjobs=[_build_cronjob()])

    with patch(
        "export_dotenv.cli.ask_for_resource",
        return_value="nightly-backup",
    ) as ask:
        name = _select_resource_name(
            out=create_output(),
            kind=Kind.CRONJOB,
            api=api,
        )

    assert name == "nightly-backup"
    ask.assert_called_once_with(
        resources=["nightly-backup"],
        kind=Kind.CRONJOB,
    )


def test_print_kubeconfig_emits_notes_for_all_fields():
    out = Mock()
    config = ResolvedKubeConfig(
        context="ctx",
        namespace=NS,
        kubeconfig="/tmp/kcfg",
    )

    _print_kubeconfig(out, config)

    assert out.note.call_count == 3
